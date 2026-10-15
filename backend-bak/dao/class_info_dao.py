"""
班级 dao 层
包含：数据库增删改查 + 简单的业务判断（如老师是否存在）
注意：已剥离学生模块，删除班级时不再检查学生。
"""
from sqlalchemy.orm import Session
from model.class_info import ClassInfo, ClassTeacherRelation, Teacher,Student,Score
from database import serialize


class BusinessError(Exception):
    """自定义业务异常"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


def get_class(db: Session, class_no: str):
    """根据班级编号（class_no）查班级"""
    return db.query(ClassInfo).filter(ClassInfo.class_no == class_no).first()


def list_classes(db: Session, class_name: str = None, page: int = 1, page_size: int = 10):
    """查询班级列表（支持模糊查询和分页）"""
    query = db.query(ClassInfo)
    if class_name:
        query = query.filter(ClassInfo.class_name.like(f"%{class_name}%"))
    total = query.count()
    items = query.order_by(ClassInfo.class_no).offset((page - 1) * page_size).limit(page_size).all()
    return total, items


def class_to_dict(cls: ClassInfo):
    """将ORM对象序列化为字典，便于JSON响应"""
    return serialize(cls)


def update_class(db: Session, class_no: str, payload):
    """更新班级"""
    cls = get_class(db, class_no)
    if not cls:
        raise BusinessError(404, "班级不存在")
    exclude_unset = True
    # 实现局部更新，只更新前端传递的字段
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(cls, key, value)
    db.commit()
    db.refresh(cls)
    return class_to_dict(cls)


def delete_class(db: Session, class_no: str):
    """删除班级（带删除保护 + 清理中间表）"""
    # 1. 先查班级是否存在
    cls = get_class(db, class_no)
    if not cls:
        raise BusinessError(404, "班级不存在")

    # 2. 检查班级下有没有学生，有则拦截
    student_count = db.query(Student).filter(Student.class_id == cls.id).count()
    if student_count > 0:
        raise BusinessError(400, f"该班级下仍有 {student_count} 名学生，不能删除")

    # 3. 必须先删除中间表关联的老师记录，否则外键约束会导致删除失败报500！
    db.query(ClassTeacherRelation).filter(ClassTeacherRelation.class_id == cls.id).delete()

    # 4. 清理完毕，才允许删除班级
    db.delete(cls)
    db.commit()

def get_class_with_teachers(db: Session, class_no: str):
    """查询班级详情，并带出这个班的班主任和授课老师姓名"""
    cls = get_class(db, class_no)
    if not cls:
        return None

    relations = db.query(ClassTeacherRelation).filter(
        ClassTeacherRelation.class_id == cls.id,
        ClassTeacherRelation.is_deleted == 0
    ).all()

    teachers = []
    for rel in relations:
        teacher = db.query(Teacher).filter(Teacher.id == rel.teacher_id).first()
        if teacher:
            teachers.append({
                "teacher_name": teacher.name,
                "relation_type": rel.relation_type
            })

    data = serialize(cls)
    data["teachers"] = teachers
    return data


def create_class(db: Session, payload):
    """新增班级（同时关联老师）"""
    # 1. 检查班级编号是否重复
    if get_class(db, payload.class_no):
        raise BusinessError(400, "班级编号已存在")

    # 2. 先把班级数据写进 classes 表，注意把 payload 里的老师 ID 排除掉
    class_data = payload.model_dump(exclude={"head_teacher_id", "teacher_id"})
    cls = ClassInfo(**class_data)
    db.add(cls)
    db.commit()
    db.refresh(cls)  # 拿到自动生成的 id

    # 3. 往中间表 class_teacher_relations 插入数据
    if payload.head_teacher_id:
        db.add(ClassTeacherRelation(
            class_id=cls.id,
            teacher_id=payload.head_teacher_id,
            relation_type="班主任",
            is_deleted=0
        ))
    if payload.teacher_id:
        db.add(ClassTeacherRelation(
            class_id=cls.id,
            teacher_id=payload.teacher_id,
            relation_type="授课老师",
            is_deleted=0
        ))
    db.commit()

    # 4. 返回带老师列表的详情
    return get_class_with_teachers(db, payload.class_no)

def get_class_statistics(db: Session, class_no: str):
    """
    查询班级及格率统计（真实数据版）
    """
    # 1. 先查班级
    cls = get_class(db, class_no)
    if not cls:
        return None

    # 2. 查该班级下的所有学生
    students = db.query(Student).filter(Student.class_id == cls.id).all()
    student_ids = [s.id for s in students]

    if not student_ids:
        return {
            "class_no": class_no, "class_name": cls.class_name,
            "total_students": 0, "total_scores": 0,
            "pass_count": 0, "pass_rate": "0%"
        }

    # 3. 查这些学生的有效成绩（必须过滤 is_deleted == 0，不然会把作废成绩算进去）
    scores = db.query(Score).filter(
        Score.student_id.in_(student_ids),
        Score.is_deleted == 0
    ).all()

    if not scores:
        return {
            "class_no": class_no, "class_name": cls.class_name,
            "total_students": len(student_ids), "total_scores": 0,
            "pass_count": 0, "pass_rate": "0%"
        }

    # 4. 遍历成绩，统计及格人次（>=60 分算及格）
    pass_count = 0
    for record in scores:
        if record.score and record.score >= 60:
            pass_count += 1

    # 5. 计算及格率，保留两位小数
    pass_rate = round(pass_count / len(scores) * 100, 2)

    return {
        "class_no": class_no,
        "class_name": cls.class_name,
        "total_students": len(student_ids),  # 班级总人数
        "total_scores": len(scores),          # 有效考试人次
        "pass_count": pass_count,             # 及格人次
        "pass_rate": f"{pass_rate}%"          # 及格率
    }