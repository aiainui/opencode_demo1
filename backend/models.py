from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="annotator")
    created_at = Column(DateTime, default=datetime.utcnow)

    annotations = relationship("Annotation", back_populates="user", foreign_keys="Annotation.user_id")


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
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    data_item = relationship("DataItem", back_populates="annotations")
    user = relationship("User", back_populates="annotations", foreign_keys=[user_id])