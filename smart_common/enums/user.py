import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    NEW = "new"
    CLIENT = "client"
    CLIENT_PRO = "client_pro"
    DEMO = "demo"
