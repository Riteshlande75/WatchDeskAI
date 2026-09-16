from app.models import get_db_connection, Submission, Exam

def evaluate_submission(submission_id):
    """
    Evaluates candidate answers, calculates total score & percentage,
    and marks the submission status as 'completed'.
    Returns the updated submission dictionary.
    """
    sub = Submission.get_by_id(submission_id)
    if not sub or sub['status'] == 'completed':
        return sub

    questions = Exam.get_questions_by_exam(sub['exam_id'])
    saved_answers = Submission.get_submission_answers(submission_id)

    score = 0
    total_possible = 0

    for q in questions:
        q_id = q['id']
        q_marks = q['marks']
        correct_opt = q['correct_option']
        total_possible += q_marks

        user_ans = saved_answers.get(q_id)
        if user_ans and user_ans['selected_option'] == correct_opt:
            score += q_marks

    percentage = round((score / total_possible) * 100, 1) if total_possible > 0 else 0.0

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE submissions 
        SET score = ?, total_marks = ?, percentage = ?, status = 'completed', submitted_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (score, total_possible, percentage, submission_id))
    conn.commit()
    conn.close()

    return Submission.get_by_id(submission_id)
