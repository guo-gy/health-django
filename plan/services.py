from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from .models import Plan
from core.types import ServiceResult
from typing import Any, Optional

@transaction.atomic
def create_or_update_plans(user_id: int, **kwargs: Any) -> ServiceResult:
    """
    一个健壮的服务，用于创建或部分更新一个计划。
    - 如果提供了 'id'，则执行部分更新。
    - 如果未提供 'id'，则执行创建，并校验所有必要字段。
    """
    plan_data = kwargs
    plan_id = plan_data.get("id")

    # 将 User 的定义提到最前面，以解决 Pylance 警告并统一获取
    User = get_user_model()

    if plan_id:
        # --- 更新逻辑 ---
        # 对于更新，我们不再检查所有字段，只更新传入的字段
        
        # 从 plan_data 中移除 id，剩下的就是待更新的数据
        update_data = plan_data.copy()
        update_data.pop('id', None)

        if not update_data:
            return {"code": 300, "message": "没有提供任何要更新的字段。", "data": None}

        try:
            # 使用 filter().update() 进行高效更新
            updated_rows = Plan.objects.filter(id=plan_id, user_id=user_id).update(**update_data)
            
            if updated_rows > 0:
                return {"code": 200, "message": "计划更新成功。", "data": {"updated": 1}}
            else:
                return {"code": 404, "message": f"ID为 {plan_id} 的计划不存在或您无权修改。", "data": None}
        except Exception as e:
            return {"code": 500, "message": f"更新计划时发生数据库错误: {e}", "data": None}

    else:
        # --- 创建逻辑 ---
        # 对于创建，我们仍然需要检查所有核心字段
        title = plan_data.get("title")
        day_of_week = plan_data.get("day_of_week")
        start_time = plan_data.get("start_time")
        end_time = plan_data.get("end_time")

        if not all([title, day_of_week, start_time, end_time]):
            return {"code": 300, "message": "创建新计划时缺少必要信息（标题、星期、开始/结束时间）。", "data": None}
        
        try:
            user_instance = User.objects.get(id=user_id)
            # 确保创建时不传入 id
            plan_data.pop('id', None)
            new_plan = Plan.objects.create(user=user_instance, **plan_data)
            return {"code": 201, "message": f"成功创建了新计划 '{new_plan.title}'。", "data": {"created": 1, "id": new_plan.id}}
        
        except User.DoesNotExist:
            return {"code": 404, "message": f"ID为 {user_id} 的用户不存在。", "data": None}
        except Exception as e:
            return {"code": 500, "message": f"创建计划时发生数据库错误: {e}", "data": None}


def get_user_plans(user_id: int, day_of_week: Optional[int] = None) -> ServiceResult:
    """
    获取用户的周常计划。
    """
    try:
        plans_query = Plan.objects.filter(user_id=user_id)
        if day_of_week is not None:
            plans_query = plans_query.filter(day_of_week=day_of_week)

        plans_list = list(
            plans_query.order_by('start_time').values(
                "id", "title", "description", "day_of_week", 
                "start_time", "end_time", "is_completed",
            )
        )
        
        for plan in plans_list:
            # 将 TimeField 对象格式化为 HH:MM 字符串
            if plan.get('start_time') and hasattr(plan['start_time'], 'strftime'):
                plan['start_time'] = plan['start_time'].strftime('%H:%M')
            if plan.get('end_time') and hasattr(plan['end_time'], 'strftime'):
                plan['end_time'] = plan['end_time'].strftime('%H:%M')

        return {
            "code": 200,
            "message": "计划获取成功。" if plans_list else "您还没有任何相关计划。",
            "data": {"plans": plans_list, "count": len(plans_list)},
        }
    except Exception as e:
        return {"code": 500, "message": f"获取计划时发生错误: {e}", "data": None}
    
def delete_plan(user_id: int, plan_id: int) -> ServiceResult:
    """
    根据 plan_id 删除一个属于指定用户的计划。
    """
    if not plan_id:
        return {"code": 300, "message": "删除计划时必须提供 plan_id。", "data": None}

    try:
        # 首先查找这个计划，确保它存在并且属于当前用户
        plan_to_delete = Plan.objects.get(id=plan_id, user_id=user_id)
        
        # 如果找到了，就删除它
        plan_to_delete.delete()
        
        return {"code": 200, "message": f"ID为 {plan_id} 的计划已成功删除。", "data": {"deleted": 1}}

    except Plan.DoesNotExist:
        # 如果找不到，说明 plan_id 不存在或不属于该用户
        return {"code": 404, "message": f"ID为 {plan_id} 的计划不存在或您无权删除。", "data": None}
    except Exception as e:
        return {"code": 500, "message": f"删除计划时发生错误: {e}", "data": None}
    
def delete_all_plans(user_id: int, day_of_week: Optional[int] = None) -> ServiceResult:
    """
    删除一个用户的所有计划。
    如果提供了 day_of_week，则只删除那一天的所有计划。
    """
    try:
        plans_to_delete = Plan.objects.filter(user_id=user_id)
        if day_of_week is not None:
            plans_to_delete = plans_to_delete.filter(day_of_week=day_of_week)
        
        # .delete() 返回一个元组，第一个元素是删除的数量
        deleted_count, _ = plans_to_delete.delete()
        
        if deleted_count > 0:
            message = f"成功清空了 {deleted_count} 条计划。"
            if day_of_week:
                message = f"成功清空了星期 {day_of_week} 的 {deleted_count} 条计划。"
            return {"code": 200, "message": message, "data": {"deleted": deleted_count}}
        else:
            return {"code": 200, "message": "您没有任何需要清空的计划。", "data": {"deleted": 0}}
            
    except Exception as e:
        return {"code": 500, "message": f"清空计划时发生错误: {e}", "data": None}
    
@transaction.atomic
def create_bulk_plans(user_id: int, plans_data: list[dict[str, Any]]) -> ServiceResult:
    """
    一次性批量创建多个计划。
    'plans_data' 是一个包含多个计划字典的列表。
    """
    User = get_user_model()
    try:
        user_instance = User.objects.get(id=user_id)
        
        # 准备要批量创建的 Plan 对象列表
        plans_to_create = []
        for plan_dict in plans_data:
            # 基础校验
            if not all(k in plan_dict for k in ['title', 'day_of_week', 'start_time', 'end_time']):
                continue # 如果缺少核心字段，就跳过这个计划
            
            plans_to_create.append(
                Plan(
                    user=user_instance,
                    title=plan_dict.get('title'),
                    description=plan_dict.get('description', ''),
                    day_of_week=plan_dict.get('day_of_week'),
                    start_time=plan_dict.get('start_time'),
                    end_time=plan_dict.get('end_time'),
                )
            )
        
        if not plans_to_create:
            return {"code": 300, "message": "没有提供任何有效的计划数据以供创建。", "data": None}

        # 使用 Django ORM 的 bulk_create 高效插入
        Plan.objects.bulk_create(plans_to_create)
        
        count = len(plans_to_create)
        return {"code": 201, "message": f"成功为您批量创建了 {count} 条新计划。", "data": {"created": count}}

    except User.DoesNotExist:
        return {"code": 404, "message": f"用户不存在。", "data": None}
    except Exception as e:
        return {"code": 500, "message": f"批量创建计划时发生错误: {e}", "data": None}
    
def get_recent_plans(user_id: int, limit: int = 5) -> ServiceResult:
    """
    获取用户最近完成或更新的N条计划。
    """
    try:
        # 按更新时间倒序排序，并取前 limit 条
        # 这里我们假设无论是运动还是饮食，只要是最近的都获取
        recent_plans_query = Plan.objects.filter(user_id=user_id, is_completed=True).order_by('-updated_at')[:limit]

        plans_list = list(
            recent_plans_query.values(
                "id", "title", "description", "start_time", "is_completed", "updated_at"
            )
        )
        
        # 格式化时间，并计算一个易于显示的相对时间
        for plan in plans_list:
            if plan.get('updated_at'):
                # 这一步也可以在前端做，但后端做更方便
                plan['display_date'] = timezone.localtime(plan['updated_at']).strftime('%Y-%m-%d %H:%M')
        
        return {
            "code": 200,
            "message": "最近计划获取成功。",
            "data": {"recent_plans": plans_list}
        }
    except Exception as e:
        return {"code": 500, "message": f"获取最近计划时发生错误: {e}", "data": None}
    
def get_over_number(user_id: int) -> ServiceResult:
    """
    获取用户最近完成或更新的N条计划。
    """
    try:
        # 按更新时间倒序排序，并取前 limit 条
        # 这里我们假设无论是运动还是饮食，只要是最近的都获取
        recent_plans_query = Plan.objects.filter(user_id=user_id, is_completed=True)

        res=recent_plans_query.count()

        return {
            "code": 200,
            "message": "完成计划数量获取成功。",
            "data": {"recent_plans_count": res}
        }
    except Exception as e:
        return {"code": 500, "message": f"获取完成计划数量时发生错误: {e}", "data": None}
    
def get_workout(user_id: int) -> ServiceResult:
    res = []
    try:
        # 按更新时间倒序排序，并取前 limit 条
        # 这里我们假设无论是运动还是饮食，只要是最近的都获取
        for i in range(1, 8):
            recent_plans_query = Plan.objects.filter(user_id=user_id, day_of_week=i, is_completed=True)
            res.append(recent_plans_query.count())
        print(res)
        return {
            "code": 200,
            "message": "完成计划数量获取成功。",
            "data": {"recent_plans_count": res}
        }
    except Exception as e:
        return {"code": 500, "message": f"获取完成计划数量时发生错误: {e}", "data": None}
    