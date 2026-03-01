from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import hashlib
import jwt
import os

app = Flask(__name__, static_folder=None)
CORS(app)

# 前端静态文件路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    full_path = os.path.join(FRONTEND_DIR, path)
    if path and os.path.exists(full_path):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')

SQLALCHEMY_DATABASE_URL = "sqlite:///./annotation.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

SECRET_KEY = "annotation-platform-secret-key"
ALGORITHM = "HS256"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="annotator")
    created_at = Column(DateTime, default=datetime.utcnow)


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")
    items = relationship("DataItem", back_populates="dataset")


class DataItem(Base):
    __tablename__ = "data_items"
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    external_id = Column(String)
    source = Column(String)
    text = Column(Text)
    extra_data = Column(JSON, default={})
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    dataset = relationship("Dataset", back_populates="items")
    annotations = relationship("Annotation", back_populates="data_item")


class Annotation(Base):
    __tablename__ = "annotations"
    id = Column(Integer, primary_key=True, index=True)
    data_item_id = Column(Integer, ForeignKey("data_items.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    label = Column(Boolean)
    remark = Column(Text, nullable=True)
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    data_item = relationship("DataItem", back_populates="annotations")


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_token(username: str) -> str:
    return jwt.encode({"sub": username}, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        return None


def get_current_user():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ')[1]
    payload = decode_token(token)
    if not payload:
        return None
    db = SessionLocal()
    user = db.query(User).filter(User.username == payload.get("sub")).first()
    db.close()
    return user


@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    db = SessionLocal()
    if db.query(User).filter(User.username == data.get("username")).first():
        db.close()
        return jsonify({"error": "Username already registered"}), 400
    new_user = User(username=data.get("username"), password_hash=get_password_hash(data.get("password", "")), role=data.get("role", "annotator"))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    result = {"id": new_user.id, "username": new_user.username, "role": new_user.role}
    db.close()
    return jsonify(result)


@app.route("/api/token", methods=["POST"])
def login():
    data = request.json
    db = SessionLocal()
    user = db.query(User).filter(User.username == data.get("username")).first()
    db.close()
    if not user or not verify_password(data.get("password", ""), user.password_hash):
        return jsonify({"error": "Incorrect username or password"}), 401
    token = create_token(user.username)
    return jsonify({"access_token": token, "token_type": "bearer"})


@app.route("/api/me", methods=["GET"])
def me():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"id": user.id, "username": user.username, "role": user.role})


@app.route("/api/users", methods=["GET"])
def list_users():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    db = SessionLocal()
    users = db.query(User).all()
    result = [{"id": u.id, "username": u.username, "role": u.role, "created_at": u.created_at.isoformat()} for u in users]
    db.close()
    return jsonify(result)


@app.route("/api/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user = get_current_user()
    if not user or user.role != "admin":
        return jsonify({"error": "No permission"}), 403
    data = request.json
    db = SessionLocal()
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        db.close()
        return jsonify({"error": "User not found"}), 404
    target_user.role = data.get("role", target_user.role)
    db.commit()
    db.close()
    return jsonify({"status": "updated"})


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = get_current_user()
    if not user or user.role != "admin":
        return jsonify({"error": "No permission"}), 403
    db = SessionLocal()
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        db.close()
        return jsonify({"error": "User not found"}), 404
    db.delete(target_user)
    db.commit()
    db.close()
    return jsonify({"status": "deleted"})


@app.route("/api/datasets", methods=["POST"])
def create_dataset():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    db = SessionLocal()
    new_dataset = Dataset(name=data["name"])
    db.add(new_dataset)
    db.commit()
    for item in data.get("items", []):
        new_item = DataItem(
            dataset_id=new_dataset.id,
            external_id=item.get("external_id", item.get("id", "")),
            source=item.get("source", "import"),
            text=item.get("text", item.get("content", "")),
            extra_data=item.get("extra_data", {})
        )
        db.add(new_item)
    db.commit()
    db.refresh(new_dataset)
    result = {"id": new_dataset.id, "name": new_dataset.name, "status": new_dataset.status}
    db.close()
    return jsonify(result)


@app.route("/api/datasets", methods=["GET"])
def list_datasets():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    db = SessionLocal()
    
    # 如果是标注员，只显示分配给自己的数据集
    if user.role == 'annotator':
        assigned_items = db.query(DataItem).filter(DataItem.assigned_to == user.id).all()
        dataset_ids = set(item.dataset_id for item in assigned_items)
        if dataset_ids:
            datasets = db.query(Dataset).filter(Dataset.id.in_(dataset_ids)).all()
        else:
            datasets = []
    else:
        datasets = db.query(Dataset).all()
    
    result = []
    for ds in datasets:
        item_count = db.query(DataItem).filter(DataItem.dataset_id == ds.id).count()
        annotated_count = db.query(Annotation).join(DataItem).filter(DataItem.dataset_id == ds.id).count()
        result.append({
            "id": ds.id, "name": ds.name, "status": ds.status,
            "created_at": ds.created_at.isoformat(), "item_count": item_count,
            "annotated_count": annotated_count
        })
    db.close()
    return jsonify(result)


@app.route("/api/datasets/<int:dataset_id>", methods=["DELETE"])
def delete_dataset(dataset_id):
    user = get_current_user()
    if not user or user.role != "admin":
        return jsonify({"error": "No permission"}), 403
    db = SessionLocal()
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        db.close()
        return jsonify({"error": "Dataset not found"}), 404
    # 删除关联的标注和数据项
    items = db.query(DataItem).filter(DataItem.dataset_id == dataset_id).all()
    for item in items:
        db.query(Annotation).filter(Annotation.data_item_id == item.id).delete()
    db.query(DataItem).filter(DataItem.dataset_id == dataset_id).delete()
    db.delete(dataset)
    db.commit()
    db.close()
    return jsonify({"status": "deleted"})


@app.route("/api/datasets/<int:dataset_id>/items", methods=["GET"])
def get_dataset_items(dataset_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    db = SessionLocal()
    items = db.query(DataItem).filter(DataItem.dataset_id == dataset_id).all()
    result = []
    for item in items:
        annotation = db.query(Annotation).filter(Annotation.data_item_id == item.id).first()
        item_data = {
            "id": item.id, "dataset_id": item.dataset_id, "external_id": item.external_id,
            "source": item.source, "text": item.text, "extra_data": item.extra_data,
            "assigned_to": item.assigned_to
        }
        if annotation:
            annotator = db.query(User).filter(User.id == annotation.user_id).first()
            reviewer = db.query(User).filter(User.id == annotation.reviewed_by).first() if annotation.reviewed_by else None
            item_data["annotation"] = {
                "id": annotation.id, "data_item_id": annotation.data_item_id,
                "user_id": annotation.user_id, 
                "annotator_name": annotator.username if annotator else None,
                "label": annotation.label,
                "remark": annotation.remark or "",
                "reviewed": annotation.reviewed, 
                "reviewed_by": annotation.reviewed_by,
                "reviewer_name": reviewer.username if reviewer else None,
                "created_at": annotation.created_at.isoformat(), 
                "updated_at": annotation.updated_at.isoformat()
            }
        result.append(item_data)
    db.close()
    return jsonify(result)


@app.route("/api/datasets/<int:dataset_id>/distribute", methods=["POST"])
def distribute_tasks(dataset_id):
    user = get_current_user()
    if not user or user.role not in ["admin", "reviewer"]:
        return jsonify({"error": "No permission"}), 403
    data = request.json
    annotator_ids = data
    db = SessionLocal()
    items = db.query(DataItem).filter(DataItem.dataset_id == dataset_id, DataItem.assigned_to == None).all()
    for i, item in enumerate(items):
        item.assigned_to = annotator_ids[i % len(annotator_ids)]
    db.commit()
    db.close()
    return jsonify({"distributed": len(items)})


@app.route("/api/annotation/next", methods=["GET"])
def get_next_annotation():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    limit = request.args.get('limit', 5, type=int)
    
    db = SessionLocal()
    
    # 找到已分配给该用户、被驳回的项目 (reviewed=True, reviewed_by=None)
    rejected_ids = db.query(Annotation.data_item_id).filter(
        Annotation.user_id == user.id,
        Annotation.reviewed == True,
        Annotation.reviewed_by == None
    ).all()
    rejected_ids = [a[0] for a in rejected_ids]
    
    # 找到已分配给该用户且已审核通过的项目 (reviewed=True, reviewed_by!=None)
    approved_ids = db.query(Annotation.data_item_id).filter(
        Annotation.user_id == user.id,
        Annotation.reviewed == True,
        Annotation.reviewed_by != None
    ).all()
    approved_ids = [a[0] for a in approved_ids]
    
    # 获取已完成的项目ID
    done_ids = rejected_ids + approved_ids
    
    # 优先获取被驳回的
    items = []
    if rejected_ids:
        rejected_items = db.query(DataItem).filter(DataItem.id.in_(rejected_ids)).limit(limit).all()
        items.extend(rejected_items)
    
    # 如果不够5条，获取未标注的
    if len(items) < limit:
        remaining = limit - len(items)
        if done_ids:
            pending_items = db.query(DataItem).filter(
                DataItem.assigned_to == user.id,
                ~DataItem.id.in_(done_ids)
            ).limit(remaining).all()
        else:
            pending_items = db.query(DataItem).filter(DataItem.assigned_to == user.id).limit(remaining).all()
        items.extend(pending_items)
    
    if not items:
        db.close()
        return jsonify({"message": "No pending tasks", "items": []})
    
    result = []
    for item in items:
        annotation = db.query(Annotation).filter(Annotation.data_item_id == item.id).first()
        item_data = {
            "id": item.id, "dataset_id": item.dataset_id, "external_id": item.external_id,
            "source": item.source, "text": item.text, "extra_data": item.extra_data,
            "assigned_to": item.assigned_to
        }
        if annotation:
            item_data["annotation"] = {
                "id": annotation.id, "data_item_id": annotation.data_item_id,
                "user_id": annotation.user_id, "label": annotation.label,
                "reviewed": annotation.reviewed, "reviewed_by": annotation.reviewed_by,
                "created_at": annotation.created_at.isoformat(), "updated_at": annotation.updated_at.isoformat()
            }
        result.append(item_data)
    
    db.close()
    return jsonify({"items": result})


@app.route("/api/annotation/dataset/<int:dataset_id>", methods=["GET"])
def get_annotation_by_dataset(dataset_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    limit = request.args.get('limit', 5, type=int)
    page = request.args.get('page', 1, type=int)
    filter_type = request.args.get('filter', 'all')
    
    db = SessionLocal()
    
    # 审核员可以标注任何未完成标注的数据，标注员只能标注分配给自己的
    if user.role in ['admin', 'reviewer']:
        all_items = db.query(DataItem).filter(DataItem.dataset_id == dataset_id).all()
    else:
        all_items = db.query(DataItem).filter(
            DataItem.dataset_id == dataset_id,
            DataItem.assigned_to == user.id
        ).all()
    
    if not all_items:
        db.close()
        return jsonify({"items": [], "total": 0, "page": 1, "total_pages": 0})
    
    # 根据筛选类型过滤
    filtered_items = []
    for item in all_items:
        annotation = db.query(Annotation).filter(Annotation.data_item_id == item.id).first()
        
        if filter_type == 'all':
            filtered_items.append((item, annotation))
        elif filter_type == 'unannotated':
            if not annotation:
                filtered_items.append((item, annotation))
        elif filter_type == 'annotated':
            if annotation and (not annotation.reviewed or not annotation.reviewed_by):
                filtered_items.append((item, annotation))
        elif filter_type == 'unreviewed':
            if annotation and not annotation.reviewed:
                filtered_items.append((item, annotation))
        elif filter_type == 'approved':
            if annotation and annotation.reviewed and annotation.reviewed_by:
                filtered_items.append((item, annotation))
        elif filter_type == 'rejected':
            if annotation and annotation.reviewed and not annotation.reviewed_by:
                filtered_items.append((item, annotation))
    
    total = len(filtered_items)
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    start = (page - 1) * limit
    end = start + limit
    filtered_items = filtered_items[start:end]
    
    result = []
    for item, annotation in filtered_items:
        item_data = {
            "id": item.id, "dataset_id": item.dataset_id, "external_id": item.external_id,
            "source": item.source, "text": item.text, "extra_data": item.extra_data,
            "assigned_to": item.assigned_to
        }
        if annotation:
            annotator = db.query(User).filter(User.id == annotation.user_id).first()
            reviewer = db.query(User).filter(User.id == annotation.reviewed_by).first() if annotation.reviewed_by else None
            item_data["annotation"] = {
                "id": annotation.id, "data_item_id": annotation.data_item_id,
                "user_id": annotation.user_id,
                "annotator_name": annotator.username if annotator else None,
                "label": annotation.label,
                "remark": annotation.remark or "",
                "reviewed": annotation.reviewed, 
                "reviewed_by": annotation.reviewed_by,
                "reviewer_name": reviewer.username if reviewer else None,
                "created_at": annotation.created_at.isoformat(), 
                "updated_at": annotation.updated_at.isoformat()
            }
        result.append(item_data)
    
    db.close()
    return jsonify({"items": result, "total": total, "page": page, "total_pages": total_pages})


@app.route("/api/annotation/<int:item_id>", methods=["POST"])
def create_annotation(item_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    db = SessionLocal()
    existing = db.query(Annotation).filter(Annotation.data_item_id == item_id).first()
    if existing:
        existing.label = data.get("label")
        existing.remark = data.get("remark", "")
        existing.updated_at = datetime.utcnow()
        existing.reviewed = False
    else:
        new_annotation = Annotation(
            data_item_id=item_id, 
            user_id=user.id, 
            label=data.get("label"),
            remark=data.get("remark", "")
        )
        db.add(new_annotation)
    db.commit()
    db.close()
    return jsonify({"status": "saved"})


@app.route("/api/annotation/<int:item_id>", methods=["PUT"])
def update_annotation(item_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    db = SessionLocal()
    existing = db.query(Annotation).filter(Annotation.data_item_id == item_id).first()
    if not existing:
        db.close()
        return jsonify({"error": "Annotation not found"}), 404
    existing.label = data.get("label")
    existing.remark = data.get("remark", "")
    existing.updated_at = datetime.utcnow()
    existing.reviewed = False
    db.commit()
    db.close()
    return jsonify({"status": "updated"})


@app.route("/api/review", methods=["POST"])
def review_annotation():
    user = get_current_user()
    if not user or user.role not in ["admin", "reviewer"]:
        return jsonify({"error": "No permission"}), 403
    data = request.json
    db = SessionLocal()
    annotation = db.query(Annotation).filter(Annotation.id == data["annotation_id"]).first()
    if not annotation:
        db.close()
        return jsonify({"error": "Annotation not found"}), 404
    annotation.reviewed = True
    annotation.reviewed_by = user.id if data["approved"] else None
    db.commit()
    db.close()
    return jsonify({"status": "reviewed"})


@app.route("/api/export/<int:dataset_id>", methods=["GET"])
def export_annotations(dataset_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    db = SessionLocal()
    items = db.query(DataItem).filter(DataItem.dataset_id == dataset_id).all()
    result = []
    for item in items:
        annotation = db.query(Annotation).filter(Annotation.data_item_id == item.id).first()
        result.append({
            "id": item.id, "external_id": item.external_id, "source": item.source,
            "text": item.text, "extra_data": item.extra_data,
            "label": annotation.label if annotation else None,
            "annotated_at": annotation.updated_at.isoformat() if annotation else None,
            "annotated_by": annotation.user_id if annotation else None
        })
    db.close()
    return jsonify(result)


if __name__ == "__main__":
    db = SessionLocal()
    if not db.query(User).filter(User.username == "admin").first():
        admin = User(username="admin", password_hash=get_password_hash("123456"), role="admin")
        db.add(admin)
        for i in range(1, 4):
            user = User(username=f"annotator{i}", password_hash=get_password_hash("123456"), role="annotator")
            db.add(user)
        db.commit()
    db.close()
    app.run(host="0.0.0.0", port=8000, debug=True)