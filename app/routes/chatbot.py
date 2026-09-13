from flask import Blueprint,request,jsonify
from flask_jwt_extended import jwt_required
from ..utils.security import current_user
from ..services.chatbot_service import answer
chatbot_bp=Blueprint('chatbot',__name__)
@chatbot_bp.post('/message')
@jwt_required()
def message():
    d=request.get_json() or {}; text=(d.get('message') or '').strip()
    if not text:return jsonify(success=False,message='Message required',error_code='VALIDATION_ERROR'),400
    return jsonify(success=True,data=answer(current_user(),text))
