import base64
import numpy as np
import cv2
from flask import Blueprint, request, jsonify, session, url_for
from functools import wraps
from app.models import Submission
from app.face_detection import face_detector
from app.scoring import evaluate_submission

events_bp = Blueprint('events', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


@events_bp.route('/exam/api/save-draft', methods=['POST'])
@login_required
def save_draft():
    """AJAX Endpoint for real-time draft answer autosaving & flag toggling."""
    try:
        user_id = session.get('user_id')
        data = request.get_json() or {}

        submission_id = data.get('submission_id')
        question_id = data.get('question_id')
        selected_option = data.get('selected_option')
        is_flagged = data.get('is_flagged')

        if not submission_id or not question_id:
            return jsonify({'success': False, 'message': 'Missing parameters'}), 400

        sub = Submission.get_by_id(submission_id)
        if not sub or sub['user_id'] != user_id or sub['status'] == 'completed':
            return jsonify({'success': False, 'message': 'Session expired or completed'}), 403

        Submission.save_draft_answer(submission_id, question_id, selected_option, is_flagged)
        return jsonify({'success': True, 'message': 'Draft saved'})
    except Exception as err:
        return jsonify({'success': False, 'message': f'Failed to save draft: {str(err)}'}), 500


@events_bp.route('/exam/api/log-violation', methods=['POST'])
@login_required
def log_violation():
    """
    Browser Activity Logging Endpoint (JavaScript + Flask).
    Logs tab switching, window focus loss, or security violations.
    Enforces automatic test submission if violation limit (5) is reached.
    """
    try:
        user_id = session.get('user_id')
        data = request.get_json() or {}

        submission_id = data.get('submission_id')
        violation_type = data.get('violation_type', 'TAB_SWITCH')
        details = data.get('details', 'Browser tab switch or window focus lost detected.')

        if not submission_id:
            return jsonify({'success': False, 'message': 'Missing submission_id'}), 400

        sub = Submission.get_by_id(submission_id)
        if not sub or sub['user_id'] != user_id:
            return jsonify({'success': False, 'message': 'Unauthorized submission session'}), 403

        if sub['status'] == 'completed':
            return jsonify({
                'success': False,
                'auto_submitted': True,
                'redirect_url': url_for('exam.exam_result', submission_id=submission_id),
                'message': 'Exam is already completed'
            })

        Submission.log_violation(submission_id, user_id, violation_type, details)
        total_violations = Submission.get_violation_count(submission_id)

        auto_submitted = False
        # Auto submit test if candidate accumulates 5 or more violations
        if total_violations >= 5 and sub['status'] == 'in_progress':
            evaluate_submission(submission_id)
            auto_submitted = True

        return jsonify({
            'success': True,
            'violation_count': total_violations,
            'auto_submitted': auto_submitted,
            'redirect_url': url_for('exam.exam_result', submission_id=submission_id),
            'message': f'Violation logged ({violation_type})'
        })
    except Exception as err:
        return jsonify({'success': False, 'message': f'Failed to log violation: {str(err)}'}), 500



@events_bp.route('/exam/api/proctor/frame', methods=['POST'])
@login_required
def proctor_frame():
    """
    OpenCV Face Monitoring API Endpoint (OpenCV + Python).
    Receives live webcam frame, runs OpenCV face detection, and logs violations for missing or multiple faces.
    Enforces automatic test submission if violation limit (5) is reached.
    """
    user_id = session.get('user_id')
    data = request.get_json() or {}

    submission_id = data.get('submission_id')
    image_data = data.get('image_data')
    should_log = data.get('should_log', False)

    if not submission_id or not image_data:
        return jsonify({'success': False, 'message': 'Missing frame data'}), 400

    sub = Submission.get_by_id(submission_id)
    if not sub or sub['user_id'] != user_id or sub['status'] == 'completed':
        return jsonify({'success': False, 'message': 'Session inactive'}), 403

    try:
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        image_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({'success': False, 'status': 'FRAME_ERROR'})

        analysis = face_detector.analyze_integrity(img)
        face_count = analysis['face_count']
        status_code = analysis['status']
        integrity_score = analysis['integrity_score']
        detail_msg = analysis['message']

        if status_code == 'NO_FACE' and should_log:
            Submission.log_violation(submission_id, user_id, "NO_FACE", detail_msg)
        elif status_code == 'MULTIPLE_FACES':
            Submission.log_violation(submission_id, user_id, "MULTIPLE_FACES", detail_msg)

        total_violations = Submission.get_violation_count(submission_id)

        auto_submitted = False
        # Auto submit test if candidate accumulates 5 or more violations
        if total_violations >= 5 and sub['status'] == 'in_progress':
            evaluate_submission(submission_id)
            auto_submitted = True

        return jsonify({
            'success': True,
            'status': status_code,
            'face_count': face_count,
            'integrity_score': integrity_score,
            'total_violations': total_violations,
            'auto_submitted': auto_submitted,
            'redirect_url': url_for('exam.exam_result', submission_id=submission_id),
            'message': detail_msg
        })

    except Exception as err:
        print(f"OpenCV Face Detection notice: {err}")
        return jsonify({'success': False, 'status': 'ERROR', 'message': str(err)})
