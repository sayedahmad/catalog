from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    email = Column(String(250), nullable=False, unique=True)
    name = Column(String(250))

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'email': self.email,
            'name': self.name,
            'id': self.id,
        }



class Catagories(Base):
    __tablename__ = 'catagories'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship(User)

    @property
    def serialize(self):
        return{
            'name'      : self.name,
            'id'        : self.id,
            'user_id'   : self.user_id
        }

class Items(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    title = Column(String(100))
    description = Column(String(500), nullable=True)
    catagory_id = Column(Integer, ForeignKey('catagories.id'))
    catagories = relationship(Catagories)

    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship(User)


    @property
    def serialize(self):
        return{
            'title'          : self.title,
            'description'   : self.description,
            'id'            : self.id,
            'user_id'   : self.user_id
        }

engine = create_engine('sqlite:///catalog.db')
Base.metadata.create_all(engine)