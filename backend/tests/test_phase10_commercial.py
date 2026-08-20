from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.models.commercial import AIModelPricing, OrganizationSubscription, FeatureFlag
from app.models.tenant import Organization, Plan, UsageEvent
from app.models.user import User
from app.services.platform_service import feature_enabled
from app.services.usage_cost_service import UsageCostService


def _register(client):
    client.post('/api/v1/auth/register', json={'username': 'admin10', 'email': 'admin10@example.com', 'password': 'secret123'})
    login = client.post('/api/v1/auth/login', json={'username': 'admin10', 'password': 'secret123'}).json()['data']
    return {'Authorization': f"Bearer {login['access_token']}"}


def test_platform_admin_and_mock_subscription_flow(client, db):
    headers = _register(client)
    user = db.query(User).filter(User.username == 'admin10').one(); user.platform_role = 'platform_admin'; db.flush()
    plan = client.post('/api/v1/admin/plans', headers=headers, json={'code': 'team10', 'name': 'TEST Team', 'member_limit': 10, 'project_limit': 50, 'ai_token_limit': 5000000, 'storage_bytes_limit': 20 * 1024 * 1024 * 1024, 'features': {'pdf_export': True}, 'price_amount': '99.00'}).json()['data']
    assert plan['price_amount'] == '99.00'
    org = client.get('/api/v1/organizations', headers=headers).json()['data'][0]
    order = client.post('/api/v1/billing/orders', params={'organization_id': org['id']}, headers=headers, json={'plan_id': plan['id']}).json()['data']
    result = client.post(f"/api/v1/dev/payments/{order['id']}/simulate-success", headers=headers).json()['data']
    assert result['status'] == 'succeeded'
    assert client.get(f"/api/v1/organizations/{org['id']}/subscription", headers=headers).json()['data']['status'] == 'active'
    assert client.get('/api/v1/admin/dashboard', headers=headers).json()['code'] == 0


def test_feature_override_and_pricing_version(db):
    org = db.query(Organization).first()
    if org is None:
        return
    flag = FeatureFlag(key='ai_review', enabled=True); db.add(flag); db.flush()
    assert feature_enabled(db, 'ai_review') is True
    event = UsageEvent(organization_id=org.id, usage_type='llm_input_tokens', quantity=1_000_000, unit='token', provider='test', model='m1', source_key='cost10')
    db.add(event); db.flush()
    pricing = AIModelPricing(provider='test', model='m1', input_price_per_million_tokens=Decimal('2.50'), output_price_per_million_tokens=Decimal('0'), effective_from=datetime.now(timezone.utc) - timedelta(days=1))
    db.add(pricing); db.flush()
    cost = UsageCostService.calculate(db, event)
    assert cost.estimated_cost == Decimal('2.50000000')
    assert UsageCostService.calculate(db, event).id == cost.id
