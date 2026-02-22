def test_noop_task_returns_completed_status():
    """Test the no-op task executes synchronously and returns expected result."""
    from pipeline.tasks.test_noop import test_pipeline_task

    result = test_pipeline_task.apply(args=["test-observation-uuid-123"])

    assert result.successful()
    task_output = result.result
    assert task_output["observation_uuid"] == "test-observation-uuid-123"
    assert task_output["status"] == "completed"


def test_noop_task_handles_different_uuids():
    """Test the task works with any observation UUID."""
    from pipeline.tasks.test_noop import test_pipeline_task

    result = test_pipeline_task.apply(
        args=["550e8400-e29b-41d4-a716-446655440000"]
    )

    assert result.successful()
    task_output = result.result
    assert (
        task_output["observation_uuid"]
        == "550e8400-e29b-41d4-a716-446655440000"
    )
