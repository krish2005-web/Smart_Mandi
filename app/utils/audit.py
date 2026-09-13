from flask import request
from flask_jwt_extended import get_jwt_identity
from ..extensions import db
from ..models import AuditLog

def audit(action, resource, resource_id=None):
    actor=None
    try: actor=get_jwt_identity()
    except Exception: pass
    db.session.add(AuditLog(actor_user_id=actor,action=action,resource=resource,resource_id=str(resource_id) if resource_id else None,ip_address=request.remote_addr,user_agent=request.headers.get('User-Agent','')[:512]))
