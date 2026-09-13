from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity
from ..models import User, Role

def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims=get_jwt()
            if claims.get('role') not in [r.value if hasattr(r,'value') else r for r in roles]:
                return jsonify(success=False,message='Forbidden',error_code='FORBIDDEN'),403
            return fn(*args, **kwargs)
        return wrapper
    return deco

def current_user():
    uid=get_jwt_identity()
    return User.query.get(uid) if uid else None

def json_error(message, code, status=400):
    return jsonify(success=False,message=message,error_code=code),status
