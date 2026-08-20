from services.recruiter_service import toggle_job_active_service


def test_toggle_job_active_not_found(mock_db):
    mock_db.fetchone.return_value = None
    result = toggle_job_active_service(user_id=2, job_id=99)
    assert result["success"] is False
    assert result["message"] == "Job not found."


def test_toggle_job_active_success(mock_db):
    mock_db.fetchone.return_value = {"is_active": True, "job_title": "Test Job"}
    result = toggle_job_active_service(user_id=2, job_id=1)

    assert result["success"] is True
    assert "closed" in result["message"]
    # Check that update was called with new_state = False
    args = mock_db.execute.call_args_list[-1][0]
    assert "UPDATE jobs SET is_active = %s" in args[0]
    assert args[1][0] is False  # new_state
