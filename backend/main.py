from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import json
from pydantic import BaseModel

from database import engine, Base, SessionLocal
from models import User, Dataset, DataItem, Annotation
from schemas import (
    UserResponse, Token,
    DatasetCreate, DatasetResponse, DataItemResponse,
    AnnotationCreate, AnnotationUpdate, AnnotationResponse,
    DataItemWithAnnotation, ReviewRequest
)
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, get_db
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Annotation Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "annotator"


@app.post("/api/register", response_model=UserResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == request.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(request.password)
    new_user = User(username=request.username, password_hash=hashed_password, role=request.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/api/token", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/api/datasets", response_model=DatasetResponse)
def create_dataset(dataset: DatasetCreate, db: Session = Depends(get_db)):
    new_dataset = Dataset(name=dataset.name)
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)

    for item in dataset.items:
        new_item = DataItem(
            dataset_id=new_dataset.id,
            external_id=item.external_id,
            source=item.source,
            text=item.text,
            extra_data=item.extra_data or {}
        )
        db.add(new_item)
    db.commit()

    return new_dataset


@app.get("/api/datasets", response_model=List[DatasetResponse])
def list_datasets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    datasets = db.query(Dataset).all()
    result = []
    for ds in datasets:
        item_count = db.query(DataItem).filter(DataItem.dataset_id == ds.id).count()
        annotated_count = db.query(DataItem).join(Annotation).filter(
            DataItem.dataset_id == ds.id
        ).count()
        ds_response = DatasetResponse(
            id=ds.id, name=ds.name, status=ds.status,
            created_at=ds.created_at, item_count=item_count,
            annotated_count=annotated_count
        )
        result.append(ds_response)
    return result


@app.get("/api/datasets/{dataset_id}/items", response_model=List[DataItemWithAnnotation])
def get_dataset_items(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items = db.query(DataItem).filter(DataItem.dataset_id == dataset_id).all()
    result = []
    for item in items:
        annotation = db.query(Annotation).filter(
            Annotation.data_item_id == item.id
        ).first()
        item_dict = DataItemWithAnnotation(
            id=item.id,
            dataset_id=item.dataset_id,
            external_id=item.external_id,
            source=item.source,
            text=item.text,
            extra_data=item.extra_data,
            assigned_to=item.assigned_to,
            annotation=AnnotationResponse(
                id=annotation.id,
                data_item_id=annotation.data_item_id,
                user_id=annotation.user_id,
                label=annotation.label,
                reviewed=annotation.reviewed,
                reviewed_by=annotation.reviewed_by,
                created_at=annotation.created_at,
                updated_at=annotation.updated_at
            ) if annotation else None
        )
        result.append(item_dict)
    return result


@app.post("/api/datasets/{dataset_id}/distribute")
def distribute_tasks(
    dataset_id: int,
    annotator_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "reviewer"]:
        raise HTTPException(status_code=403, detail="No permission")

    items = db.query(DataItem).filter(
        DataItem.dataset_id == dataset_id,
        DataItem.assigned_to.is_(None)
    ).all()

    for i, item in enumerate(items):
        item.assigned_to = annotator_ids[i % len(annotator_ids)]

    db.commit()
    return {"distributed": len(items)}


@app.get("/api/annotation/next")
def get_next_annotation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(DataItem).filter(
        DataItem.assigned_to == current_user.id
    ).first()

    if not item:
        return {"message": "No pending tasks"}

    annotation = db.query(Annotation).filter(
        Annotation.data_item_id == item.id
    ).first()

    return {
        "item": DataItemResponse.model_validate(item),
        "annotation": AnnotationResponse.model_validate(annotation) if annotation else None
    }


@app.post("/api/annotation/{item_id}")
def create_annotation(
    item_id: int,
    annotation: AnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(DataItem).filter(DataItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    existing = db.query(Annotation).filter(
        Annotation.data_item_id == item_id
    ).first()

    if existing:
        existing.label = annotation.label
        existing.updated_at = datetime.utcnow()
    else:
        new_annotation = Annotation(
            data_item_id=item_id,
            user_id=current_user.id,
            label=annotation.label
        )
        db.add(new_annotation)

    db.commit()
    return {"status": "saved"}


@app.put("/api/annotation/{item_id}")
def update_annotation(
    item_id: int,
    annotation: AnnotationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(Annotation).filter(
        Annotation.data_item_id == item_id
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Annotation not found")

    existing.label = annotation.label
    existing.updated_at = datetime.utcnow()
    existing.reviewed = False
    db.commit()
    return {"status": "updated"}


@app.post("/api/review")
def review_annotation(
    review: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "reviewer"]:
        raise HTTPException(status_code=403, detail="No permission")

    annotation = db.query(Annotation).filter(Annotation.id == review.annotation_id).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    annotation.reviewed = True
    annotation.reviewed_by = current_user.id if review.approved else None
    db.commit()
    return {"status": "reviewed"}


@app.get("/api/export/{dataset_id}")
def export_annotations(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items = db.query(DataItem).filter(DataItem.dataset_id == dataset_id).all()
    result = []
    for item in items:
        annotation = db.query(Annotation).filter(
            Annotation.data_item_id == item.id
        ).first()
        result.append({
            "id": item.id,
            "external_id": item.external_id,
            "source": item.source,
            "text": item.text,
            "extra_data": item.extra_data,
            "label": annotation.label if annotation else None,
            "annotated_at": annotation.updated_at.isoformat() if annotation else None,
            "annotated_by": annotation.user_id if annotation else None
        })
    return result


from datetime import datetime