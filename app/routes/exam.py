import csv
from io import StringIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, Response
from functools import wraps
from app.models import User, Exam, Submission
from app.scoring import evaluate_submission

exam_bp = Blueprint('exam', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access the examination area.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@exam_bp.route('/dashboard', endpoint='dashboard')
@exam_bp.route('/dashboard', endpoint='candidate_dashboard')
@login_required
def dashboard():
    """Candidate Dashboard: Available exams, attempt metrics, and test history."""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id) if user_id else None
    
    candidate_name = (user['full_name'] if user and user.get('full_name') else session.get('full_name')) or 'Candidate'
    photo_path = (user['photo_path'] if user and user.get('photo_path') else session.get('photo_path'))

    if user:
        session['full_name'] = candidate_name
        if photo_path:
            session['photo_path'] = photo_path

    available_exams = Exam.get_all()
    user_submissions = Submission.get_user_submissions(user_id)
    is_sample_data = False
    if not user_submissions:
        user_submissions = Submission.get_all_submissions()
        is_sample_data = True

    if not user_submissions:
        user_submissions = [
            {
                'id': 1,
                'user_id': user_id,
                'exam_id': 1,
                'exam_title': 'Machine Learning Fundamentals',
                'exam_category': 'Artificial Intelligence',
                'started_at': '2026-08-01 10:00:00',
                'submitted_at': '2026-08-01 10:25:00',
                'score': 4,
                'total_marks': 5,
                'percentage': 80.0,
                'pass_percentage': 60,
                'status': 'completed',
                'violation_count': 0,
                'integrity_score': 100.0,
                'face_presence': '100.0%'
            },
            {
                'id': 2,
                'user_id': user_id,
                'exam_id': 2,
                'exam_title': 'Data Structures & Algorithms Evaluation',
                'exam_category': 'Computer Science',
                'started_at': '2026-08-02 14:15:00',
                'submitted_at': '2026-08-02 14:35:00',
                'score': 3,
                'total_marks': 4,
                'percentage': 75.0,
                'pass_percentage': 75,
                'status': 'completed',
                'violation_count': 0,
                'integrity_score': 98.5,
                'face_presence': '99.0%'
            },
            {
                'id': 3,
                'user_id': user_id,
                'exam_id': 3,
                'exam_title': 'Web Security Essentials',
                'exam_category': 'Cybersecurity',
                'started_at': '2026-08-03 16:00:00',
                'submitted_at': '2026-08-03 16:20:00',
                'score': 2,
                'total_marks': 5,
                'percentage': 40.0,
                'pass_percentage': 60,
                'status': 'completed',
                'violation_count': 1,
                'integrity_score': 92.0,
                'face_presence': '95.0%'
            }
        ]
        is_sample_data = True

    # Enrich submissions with proctor audit summary metrics
    for sub in user_submissions:
        try:
            logs = Submission.get_proctor_logs(sub['id'])
            sub['violation_count'] = len(logs)
            integ = IntegrityScorer.calculate_session_integrity(sub['id'])
            sub['integrity_score'] = integ.get('integrity_score', 100.0)
            sub['face_presence'] = f"{integ.get('face_presence_ratio', 100.0)}%"
        except Exception:
            sub.setdefault('violation_count', 0)
            sub.setdefault('integrity_score', 100.0)
            sub.setdefault('face_presence', "100.0%")

    total_attempts = len(user_submissions)
    completed_submissions = [s for s in user_submissions if s.get('status') == 'completed']
    
    # Use completed submissions if available for passing and average metrics
    metrics_source = completed_submissions if completed_submissions else user_submissions
    metrics_count = len(metrics_source)

    passed_attempts = sum(1 for s in metrics_source if (s.get('percentage') or 0) >= (s.get('pass_percentage') or 60))
    avg_score = round(sum(s.get('percentage') or 0 for s in metrics_source) / metrics_count, 1) if metrics_count > 0 else 0.0
    pass_rate = round((passed_attempts / metrics_count * 100), 1) if metrics_count > 0 else 0.0

    stats = {
        'available_count': len(available_exams),
        'total_attempts': total_attempts,
        'passed_attempts': passed_attempts,
        'avg_score': avg_score,
        'pass_rate': pass_rate
    }

    analytics_data = get_candidate_analytics(user_id)

    return render_template(
        'dashboard/dashboard.html',
        user=user,
        candidate_name=candidate_name,
        photo_path=photo_path,
        exams=available_exams,
        available_exams=available_exams,
        submissions=user_submissions,
        history=user_submissions,
        stats=stats,
        total_attempts=total_attempts,
        passed_attempts=passed_attempts,
        avg_score=avg_score,
        analytics=analytics_data,
        is_sample_data=is_sample_data
    )


def get_candidate_analytics(user_id):
    """Computes Score Trend, Category Mastery, and Strengths & Weaknesses."""
    submissions = Submission.get_user_submissions(user_id)
    if not submissions:
        submissions = Submission.get_all_submissions()
    
    # Filter for completed attempts to avoid distorting performance with in-progress sessions
    completed_subs = [s for s in submissions if s.get('status') == 'completed']
    target_subs = completed_subs if completed_subs else submissions

    # 1. Chronological Score Trend
    chronological = sorted(target_subs, key=lambda s: s.get('submitted_at') or s.get('started_at') or '')
    trend_labels = []
    trend_values = []
    trend_items = []
    
    for idx, s in enumerate(chronological):
        full_title = s.get('exam_title', f'Exam #{idx+1}')
        date_str = ((s.get('submitted_at') or s.get('started_at') or '')[:10])
        pct = s.get('percentage')
        if pct is None:
            pct = 0.0

        short_label = f"Attempt #{idx+1}"
        trend_labels.append(short_label)
        trend_values.append(pct)
        trend_items.append({
            'label': short_label,
            'title': full_title,
            'date': date_str or 'Recent',
            'score': pct
        })

    if not trend_labels or not completed_subs:
        # Default sample baseline preview if no completed tests yet
        trend_labels = ['Attempt #1', 'Attempt #2', 'Attempt #3', 'Attempt #4']
        trend_values = [68, 75, 84, 90]
        trend_items = [
            {'label': 'Attempt #1', 'title': 'Initial Diagnostic Assessment', 'date': '2026-07-20', 'score': 68},
            {'label': 'Attempt #2', 'title': 'Practice Mock Test 1', 'date': '2026-07-22', 'score': 75},
            {'label': 'Attempt #3', 'title': 'Mid-Term Evaluation', 'date': '2026-07-25', 'score': 84},
            {'label': 'Attempt #4', 'title': 'Final Preparation Exam', 'date': '2026-07-28', 'score': 90}
        ]

    # 2. Category Mastery Breakdown
    category_scores = {}
    for s in target_subs:
        cat = s.get('exam_category') or s.get('category') or 'Computer Science'
        pct = s.get('percentage')
        if pct is None:
            pct = 0.0
        if cat not in category_scores:
            category_scores[cat] = []
        category_scores[cat].append(pct)

    category_mastery = {}
    for cat, scores in category_scores.items():
        category_mastery[cat] = round(sum(scores) / len(scores), 1)

    if not category_mastery or not completed_subs:
        category_mastery = {
            'Computer Science': 88.5,
            'Cybersecurity': 72.0,
            'Data Science': 84.0,
            'Artificial Intelligence': 65.0
        }

    # 3. Strengths & Weaknesses Categorization
    strengths = []
    weaknesses = []
    for cat, avg_pct in category_mastery.items():
        if avg_pct >= 75.0:
            strengths.append({'category': cat, 'score': avg_pct})
        else:
            weaknesses.append({'category': cat, 'score': avg_pct})

    strengths = sorted(strengths, key=lambda x: x['score'], reverse=True)
    weaknesses = sorted(weaknesses, key=lambda x: x['score'])

    return {
        'trend_labels': trend_labels,
        'trend_values': trend_values,
        'trend_items': trend_items,
        'category_mastery': category_mastery,
        'category_labels': list(category_mastery.keys()),
        'category_avg': list(category_mastery.values()),
        'strengths': strengths,
        'weaknesses': weaknesses
    }


@exam_bp.route('/exam/api/analytics')
@login_required
def api_analytics():
    """AJAX Endpoint returning candidate analytics JSON."""
    user_id = session.get('user_id')
    data = get_candidate_analytics(user_id)
    return jsonify({'success': True, 'analytics': data})


@exam_bp.route('/exam/<int:exam_id>/system-check')
@login_required
def system_check(exam_id):
    """Pre-exam hardware environment check screen."""
    exam = Exam.get_by_id(exam_id)
    if not exam:
        flash('Exam not found.', 'error')
        return redirect(url_for('exam.dashboard'))

    return render_template('exam/system_check.html', exam=exam)


@exam_bp.route('/exam/<int:exam_id>/start', methods=['POST'])
@login_required
def start_exam(exam_id):
    """Initializes/retrieves an in-progress submission session and opens exam room."""
    user_id = session.get('user_id')
    exam = Exam.get_by_id(exam_id)
    if not exam:
        flash('Invalid exam selected.', 'error')
        return redirect(url_for('exam.dashboard'))

    submission = Submission.create_or_get_in_progress(user_id, exam_id)
    return redirect(url_for('exam.exam_room', submission_id=submission['id']))


@exam_bp.route('/exam/submission/<int:submission_id>/room')
@login_required
def exam_room(submission_id):
    """Renders live interactive exam room."""
    user_id = session.get('user_id')
    sub = Submission.get_by_id(submission_id)

    if not sub or sub['user_id'] != user_id:
        flash('Submission session not found or unauthorized.', 'error')
        return redirect(url_for('exam.dashboard'))

    if sub['status'] == 'completed':
        flash('This exam has already been submitted.', 'info')
        return redirect(url_for('exam.exam_result', submission_id=submission_id))

    exam = Exam.get_by_id(sub['exam_id'])
    questions = Exam.get_questions_by_exam(sub['exam_id'])
    saved_answers = Submission.get_submission_answers(submission_id)
    violation_count = Submission.get_violation_count(submission_id)

    return render_template(
        'exam/exam_room.html',
        submission=sub,
        exam=exam,
        questions=questions,
        saved_answers=saved_answers,
        violation_count=violation_count
    )


@exam_bp.route('/exam/submission/<int:submission_id>/submit', methods=['POST'])
@login_required
def submit_exam(submission_id):
    """Final submission endpoint. Evaluates answers and redirects to results breakdown."""
    user_id = session.get('user_id')
    sub = Submission.get_by_id(submission_id)

    if not sub or sub['user_id'] != user_id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('exam.dashboard'))

    completed_sub = evaluate_submission(submission_id)
    flash('Exam submitted successfully!', 'success')
    return redirect(url_for('exam.exam_result', submission_id=submission_id))


from app.integrity_scoring import IntegrityScorer

@exam_bp.route('/exam/submission/<int:submission_id>/result')
@login_required
def exam_result(submission_id):
    """Exam Result View: Score, performance breakdown, and Pandas Integrity Score analysis."""
    user_id = session.get('user_id')
    sub = Submission.get_by_id(submission_id)

    if not sub or sub['user_id'] != user_id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('exam.dashboard'))

    exam = Exam.get_by_id(sub['exam_id'])
    questions = Exam.get_questions_by_exam(sub['exam_id'])
    saved_answers = Submission.get_submission_answers(submission_id)
    proctor_logs = Submission.get_proctor_logs(submission_id)
    violation_count = len(proctor_logs)

    # Compute Pandas-Powered Weighted Integrity Score & Face Presence Ratio
    integrity_data = IntegrityScorer.calculate_session_integrity(submission_id)

    review_list = []
    correct_count = 0

    for q in questions:
        q_id = q['id']
        user_ans = saved_answers.get(q_id, {})
        sel_opt = user_ans.get('selected_option', -1)
        is_correct = (sel_opt == q['correct_option'])
        if is_correct:
            correct_count += 1

        review_list.append({
            'question_text': q['question_text'],
            'options': q['options'],
            'user_selected': sel_opt,
            'correct_option': q['correct_option'],
'is_correct': is_correct,
            'marks': q['marks']
        })

    sub_pct = sub.get('percentage') or 0.0
    pass_target = exam.get('pass_percentage', 60) if exam else 60
    is_passed = (sub_pct >= pass_target)

    return render_template(
        'exam/result.html',
        submission=sub,
        exam=exam,
        review_list=review_list,
        correct_count=correct_count,
        total_questions=len(questions),
        is_passed=is_passed,
        proctor_logs=proctor_logs,
        violation_count=violation_count,
        integrity=integrity_data
    )


@exam_bp.route('/exam/submission/<int:submission_id>/certificate')
@login_required
def exam_certificate(submission_id):
    """Official Result Certificate View for Passed Exams."""
    user_id = session.get('user_id')
    sub = Submission.get_by_id(submission_id)

    if not sub or sub['user_id'] != user_id:
        flash('Unauthorized access or certificate not found.', 'error')
        return redirect(url_for('exam.dashboard'))

    exam = Exam.get_by_id(sub['exam_id'])
    user = User.get_by_id(user_id)
    
    pct = sub.get('percentage', 0.0) or 0.0
    pass_target = exam.get('pass_percentage', 60) if exam else 60

    if sub.get('status') != 'completed' or pct < pass_target:
        flash('Certificate is only generated for completed and passed examinations.', 'warning')
        return redirect(url_for('exam.dashboard'))

    integrity_data = IntegrityScorer.calculate_session_integrity(submission_id)

    return render_template(
        'exam/certificate.html',
        submission=sub,
        exam=exam,
        user=user,
        integrity=integrity_data
    )


@exam_bp.route('/exam/submission/<int:submission_id>/quick-breakdown')
@login_required
def quick_breakdown(submission_id):
    """AJAX Endpoint returning question-by-question breakdown for Quick Review Modal."""
    user_id = session.get('user_id')
    sub = Submission.get_by_id(submission_id)

    if not sub or sub['user_id'] != user_id:
        return jsonify({'success': False, 'message': 'Unauthorized or invalid submission'}), 403

    exam = Exam.get_by_id(sub['exam_id'])
    questions = Exam.get_questions_by_exam(sub['exam_id'])
    saved_answers = Submission.get_submission_answers(submission_id)

    breakdown = []
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0

    for idx, q in enumerate(questions):
        q_id = q['id']
        user_ans = saved_answers.get(q_id, {})
        sel_opt = user_ans.get('selected_option', -1)
        
        if sel_opt == -1:
            status = 'unanswered'
            unanswered_count += 1
        elif sel_opt == q['correct_option']:
            status = 'correct'
            correct_count += 1
        else:
            status = 'incorrect'
            incorrect_count += 1

        selected_text = q['options'][sel_opt] if (0 <= sel_opt < len(q['options'])) else 'No Option Selected'
        correct_text = q['options'][q['correct_option']] if (0 <= q['correct_option'] < len(q['options'])) else 'N/A'

        breakdown.append({
            'number': idx + 1,
            'question_text': q['question_text'],
            'selected_option': sel_opt,
            'selected_text': selected_text,
            'correct_option': q['correct_option'],
            'correct_text': correct_text,
            'status': status,
            'marks': q['marks']
        })

    return jsonify({
        'success': True,
        'exam_title': exam['title'] if exam else 'Assessment',
        'score': sub.get('score', 0),
        'total_marks': sub.get('total_marks', 0),
        'percentage': sub.get('percentage', 0.0),
        'correct_count': correct_count,
        'incorrect_count': incorrect_count,
        'unanswered_count': unanswered_count,
        'total_questions': len(questions),
        'questions': breakdown
    })


@exam_bp.route('/exam/history/export')
@login_required
def export_history():
    """Generates and downloads CSV file of candidate exam result history."""
    user_id = session.get('user_id')
    submissions = Submission.get_user_submissions(user_id)

    si = StringIO()
    cw = csv.writer(si)

    # Write CSV Header
    cw.writerow([
        'Submission ID',
        'Exam Title',
        'Category',
        'Started At',
        'Submitted At',
        'Score Obtained',
        'Total Marks',
        'Percentage (%)',
        'Pass Target (%)',
        'Status',
        'Proctor Integrity (%)',
        'Violations Count'
    ])

    for sub in submissions:
        sub_id = sub['id']
        try:
            logs = Submission.get_proctor_logs(sub_id)
            v_count = len(logs)
            integ = IntegrityScorer.calculate_session_integrity(sub_id)
            integ_score = integ.get('integrity_score', 100.0)
        except Exception:
            v_count = 0
            integ_score = 100.0

        cw.writerow([
            sub['id'],
            sub.get('exam_title', 'Assessment'),
            sub.get('exam_category', 'General'),
            sub.get('started_at', ''),
            sub.get('submitted_at', ''),
            sub.get('score', 0),
            sub.get('total_marks', 0),
            sub.get('percentage', 0.0),
            sub.get('pass_percentage', 60),
            sub.get('status', 'in_progress').upper(),
            integ_score,
            v_count
        ])

    output = si.getvalue()
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=watchdesk_results_history.csv'}
    )
