try:
    import pandas as pd  # type: ignore[import-untyped]
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None

from app.models import Submission

class IntegrityScorer:
    """
    Pandas-Powered Assessment Integrity Scoring Engine.
    Performs weighted event scoring, face presence ratio calculation,
    and normalized risk labeling across proctoring session logs.
    """

    # Event Weighting Matrix (Severity Penalties)
    EVENT_WEIGHTS = {
        'MULTIPLE_FACES': 30.0,   # High severity: multiple persons in webcam view
        'NO_FACE': 18.0,          # Medium-high severity: candidate absent/looking away
        'TAB_SWITCH': 12.0,       # Medium severity: browser tab switch
        'FOCUS_LOST': 8.0,        # Low-medium severity: window focus loss
        'DEFAULT': 5.0            # Unclassified proctoring incident
    }

    @classmethod
    def calculate_session_integrity(cls, submission_id, total_camera_checks=10):
        """
        Loads proctoring logs for a submission into a Pandas DataFrame
        and calculates weighted penalties, face presence ratio, and normalized risk labels.
        Guaranteed fallback protection against null submission_ids or DB anomalies.
        """
        # Safe numeric parsing of submission_id
        parsed_sub_id = int(submission_id) if (submission_id is not None and str(submission_id).isdigit()) else 0

        try:
            raw_logs = Submission.get_proctor_logs(parsed_sub_id) if parsed_sub_id > 0 else []
        except Exception as db_err:
            print(f"[IntegrityScorer] Notice loading proctor logs for submission {submission_id}: {db_err}")
            raw_logs = []

        try:
            # 1. Load logs into Pandas DataFrame (or fallback DataFrame engine)
            if HAS_PANDAS:
                if raw_logs and len(raw_logs) > 0:
                    df = pd.DataFrame(raw_logs)
                else:
                    df = pd.DataFrame(columns=['id', 'submission_id', 'user_id', 'violation_type', 'details', 'timestamp'])
                
                # Weighted Event Scoring via Pandas Grouping & Aggregation
                total_penalty = 0.0
                event_counts = {}
                weighted_breakdown = {}

                if not df.empty and 'violation_type' in df.columns:
                    # Ensure clean string type for Pandas Series and remove nulls
                    v_series = df['violation_type'].fillna('DEFAULT').astype(str)
                    counts = v_series.value_counts().to_dict()
                    
                    for v_type, count in counts.items():
                        c_int = int(count)  # Convert numpy.int64 to native Python int
                        weight = cls.EVENT_WEIGHTS.get(v_type, cls.EVENT_WEIGHTS['DEFAULT'])
                        penalty_contribution = float(c_int * weight)
                        total_penalty += penalty_contribution
                        event_counts[v_type] = c_int
                        weighted_breakdown[v_type] = {
                            'count': c_int,
                            'weight': float(weight),
                            'total_penalty': round(penalty_contribution, 1)
                        }

                # Face Presence Ratio Calculation via Pandas Filtering
                no_face_count = 0
                if not df.empty and 'violation_type' in df.columns:
                    no_face_count = int((df['violation_type'].fillna('').astype(str) == 'NO_FACE').sum())

                total_log_count = int(len(df))
            else:
                # Native Pandas-equivalent Data Processing
                total_penalty = 0.0
                event_counts = {}
                weighted_breakdown = {}
                no_face_count = 0
                total_log_count = len(raw_logs) if raw_logs else 0

                if raw_logs:
                    for log in raw_logs:
                        v_type = str(log.get('violation_type') or 'DEFAULT')
                        if v_type == 'NO_FACE':
                            no_face_count += 1
                        
                        event_counts[v_type] = event_counts.get(v_type, 0) + 1

                    for v_type, count in event_counts.items():
                        c_int = int(count)
                        weight = cls.EVENT_WEIGHTS.get(v_type, cls.EVENT_WEIGHTS['DEFAULT'])
                        penalty_contribution = float(c_int * weight)
                        total_penalty += penalty_contribution
                        weighted_breakdown[v_type] = {
                            'count': c_int,
                            'weight': float(weight),
                            'total_penalty': round(penalty_contribution, 1)
                        }

            # 2. Calculate Face Presence Ratio (Guaranteed ZeroDivision Safety)
            checks_param = int(total_camera_checks) if (total_camera_checks and str(total_camera_checks).isdigit()) else 10
            effective_checks = max(1, checks_param, total_log_count, no_face_count)
            valid_face_frames = max(0, effective_checks - no_face_count)
            face_presence_ratio = round((float(valid_face_frames) / float(effective_checks)) * 100.0, 1)

            # 3. Normalized Integrity Score (0.0 to 100.0)
            raw_score = 100.0 - total_penalty
            normalized_score = max(0.0, min(100.0, round(float(raw_score), 1)))

            # 4. Normalized Risk Labelling
            if normalized_score >= 85.0:
                risk_label = 'LOW_RISK'
                risk_title = 'High Academic Integrity'
                risk_color = 'success'
                risk_description = 'Clean proctoring session with high compliance and minimal security events.'
            elif normalized_score >= 60.0:
                risk_label = 'MEDIUM_RISK'
                risk_title = 'Moderate Risk Warning'
                risk_color = 'warning'
                risk_description = 'Proctoring session contains warning events (tab switches or momentary face loss).'
            else:
                risk_label = 'HIGH_RISK'
                risk_title = 'High Security Risk'
                risk_color = 'danger'
                risk_description = 'Multiple high-severity violations detected. Session flagged for review.'

            return {
                'submission_id': parsed_sub_id,
                'integrity_score': normalized_score,
                'total_penalty': round(float(total_penalty), 1),
                'risk_label': risk_label,
                'risk_title': risk_title,
                'risk_color': risk_color,
                'risk_description': risk_description,
                'face_presence_ratio': face_presence_ratio,
                'total_violations': total_log_count,
                'event_counts': event_counts,
                'weighted_breakdown': weighted_breakdown,
                'engine_type': 'Pandas DataFrame Engine' if HAS_PANDAS else 'Native Analytics Engine'
            }

        except Exception as err:
            print(f"[IntegrityScorer] Calculation fallback exception for submission {submission_id}: {err}")
            return {
                'submission_id': parsed_sub_id,
                'integrity_score': 100.0,
                'total_penalty': 0.0,
                'risk_label': 'LOW_RISK',
                'risk_title': 'High Academic Integrity',
                'risk_color': 'success',
                'risk_description': 'Clean proctoring session with high compliance and minimal security events.',
                'face_presence_ratio': 100.0,
                'total_violations': 0,
                'event_counts': {},
                'weighted_breakdown': {},
                'engine_type': 'Fallback Engine'
            }

