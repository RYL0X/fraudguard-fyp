from flask import Blueprint, jsonify, request
from backend.db import get_connection

alerts_bp = Blueprint('alerts', __name__)

@alerts_bp.route('', methods=['GET'])
def get_alerts():
    """
    GET /api/alerts
    GET /api/alerts?status=new
    GET /api/alerts?status=review
    GET /api/alerts?status=resolved
    Return alerts matching the optional status filter, latest first.
    """
    status_filter = request.args.get('status')
    
    query = "SELECT * FROM alerts"
    params = ()
    
    if status_filter:
        query += " WHERE status = %s"
        params = (status_filter,)
        
    query += " ORDER BY timestamp DESC"
    
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        alerts = cur.fetchall()
        return jsonify(alerts)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@alerts_bp.route('/<alert_id>/status', methods=['PATCH'])
def update_alert_status(alert_id):
    """
    PATCH /api/alerts/<alert_id>/status
    Body: {"status": "review"} or {"status": "resolved"}
    """
    data = request.get_json() or {}
    new_status = data.get('status')
    
    if new_status not in ('new', 'review', 'resolved', 'dismissed'):
        return jsonify({'error': 'Invalid status'}), 400
        
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if new_status == 'review':
            query = "UPDATE alerts SET status = %s, reviewed_at = NOW() WHERE id = %s"
        elif new_status == 'resolved':
            query = "UPDATE alerts SET status = %s, resolved_at = NOW() WHERE id = %s"
        elif new_status == 'dismissed':
            query = "UPDATE alerts SET status = %s, resolved_at = NULL WHERE id = %s"
        else:
            query = "UPDATE alerts SET status = %s WHERE id = %s"
            
        cur.execute(query, (new_status, alert_id))
        conn.commit()
        
        if cur.rowcount == 0:
            return jsonify({'error': 'Alert not found'}), 404
            
        return jsonify({'message': 'Status updated successfully', 'status': new_status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()
