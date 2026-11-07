"""Full integration test suite covering REST API endpoints."""
import httpx
import pytest


@pytest.mark.asyncio
async def test_api_health(client: httpx.AsyncClient):
    """Verify health endpoint returns healthy status and connected database."""
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_api_models_flow(client: httpx.AsyncClient):
    """Verify listing models and registering a new model configuration."""
    list_res = await client.get("/api/v1/models")
    assert list_res.status_code == 200
    models = list_res.json()
    assert len(models) >= 1

    # Register new model
    new_model_payload = {
        "provider_name": "Mock",
        "model_identifier": "mock-api-test-model",
        "display_name": "API Test Model",
        "description": "Registered via API test",
        "default_temperature": 0.5,
        "default_max_tokens": 512,
        "cost_per_1k_input_tokens": 0.002,
        "cost_per_1k_output_tokens": 0.006,
    }
    reg_res = await client.post("/api/v1/models/register", json=new_model_payload)
    assert reg_res.status_code == 201
    created = reg_res.json()
    assert created["model_identifier"] == "mock-api-test-model"

    # Fetch by ID
    get_res = await client.get(f"/api/v1/models/{created['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["display_name"] == "API Test Model"

    # Ping health
    health_res = await client.get(f"/api/v1/models/{created['id']}/health")
    assert health_res.status_code == 200
    assert health_res.json()["is_available"] is True


@pytest.mark.asyncio
async def test_api_prompts_flow(client: httpx.AsyncClient):
    """Verify prompt creation, versioning, listing, and execution."""
    p_payload = {
        "name": "API Prompt Template",
        "description": "Created in test_api",
        "initial_template": "Context: {context}\nQuestion: {question}",
    }
    create_res = await client.post("/api/v1/prompts", json=p_payload)
    assert create_res.status_code == 201
    prompt = create_res.json()

    # List prompts
    list_res = await client.get("/api/v1/prompts")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # Add version
    v_res = await client.post(
        f"/api/v1/prompts/{prompt['id']}/versions",
        json={"template_text": "Updated Context: {context}\nQ: {question}"},
    )
    assert v_res.status_code == 201
    assert v_res.json()["version_number"] == 2

    # Execute prompt
    models_res = await client.get("/api/v1/models")
    mock_id = models_res.json()[0]["id"]

    exec_res = await client.post(
        f"/api/v1/prompts/{prompt['id']}/execute",
        json={
            "model_id": mock_id,
            "variables": {"context": "Python is fast.", "question": "What is Python?"},
        },
    )
    assert exec_res.status_code == 200
    assert exec_res.json()["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_api_datasets_flow(client: httpx.AsyncClient):
    """Verify creating and fetching datasets."""
    ds_payload = {
        "name": "API Test Dataset",
        "format": "json",
        "records": [
            {
                "question": "What is SQLAlchemy?",
                "reference_answer": "A Python SQL toolkit and ORM.",
                "contexts": ["SQLAlchemy provides enterprise-level persistence patterns."],
            }
        ],
    }
    create_res = await client.post("/api/v1/datasets", json=ds_payload)
    assert create_res.status_code == 201
    ds = create_res.json()
    assert ds["record_count"] == 1

    get_res = await client.get(f"/api/v1/datasets/{ds['id']}")
    assert get_res.status_code == 200
    assert len(get_res.json()["records"]) == 1


@pytest.mark.asyncio
async def test_api_evaluations_run(client: httpx.AsyncClient):
    """Verify ad-hoc evaluation endpoint computes metric scores."""
    eval_payload = {
        "question": "What is a database index?",
        "generated_answer": "A database index speeds up search queries on tables.",
        "reference_answer": "A database index optimizes search query retrieval times.",
    }
    res = await client.post("/api/v1/evaluations/run", json=eval_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_score"] >= 0.0
    assert len(data["metrics"]) >= 3


@pytest.mark.asyncio
async def test_api_rag_evaluations_endpoint(client: httpx.AsyncClient):
    """Verify dedicated RAG Triad assessment endpoint."""
    rag_payload = {
        "question": "What is Raft?",
        "retrieved_contexts": ["Raft is a distributed consensus protocol."],
        "generated_answer": "Raft is a distributed consensus algorithm.",
    }
    res = await client.post("/api/v1/evaluations/rag", json=rag_payload)
    assert res.status_code == 200
    data = res.json()
    assert "triad_scores" in data
    assert data["triad_scores"]["faithfulness"] >= 0.5


@pytest.mark.asyncio
async def test_api_analytics_endpoints(client: httpx.AsyncClient):
    """Verify all analytics endpoints respond with valid schemas."""
    # Overview
    ov_res = await client.get("/api/v1/analytics/overview")
    assert ov_res.status_code == 200
    assert "total_experiments" in ov_res.json()

    # Models
    m_res = await client.get("/api/v1/analytics/models")
    assert m_res.status_code == 200
    assert isinstance(m_res.json(), list)

    # Performance
    p_res = await client.get("/api/v1/analytics/performance")
    assert p_res.status_code == 200
    assert "score_distribution" in p_res.json()

    # Failures
    f_res = await client.get("/api/v1/analytics/failures")
    assert f_res.status_code == 200
    assert "breakdown_by_category" in f_res.json()


@pytest.mark.asyncio
async def test_api_error_validation_cases(client: httpx.AsyncClient):
    """Verify error handling on non-existent resources and malformed bodies."""
    # 404 on unknown model
    res_404 = await client.get("/api/v1/models/999999")
    assert res_404.status_code == 404

    # 400 on empty generated answer in evaluation
    res_400 = await client.post("/api/v1/evaluations/run", json={"question": "Q", "generated_answer": ""})
    assert res_400.status_code == 400

