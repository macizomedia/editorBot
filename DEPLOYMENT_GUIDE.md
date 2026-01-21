# Template Integration Deployment Guide

**Date:** 21 January 2026  
**Branch:** Development  
**Status:** Ready for EC2 Deployment

---

## ✅ Completed Work

### Session 1: Foundation
- ✅ Created `bot/templates/` module structure
- ✅ Implemented type-safe dataclasses (models.py)
- ✅ Implemented API client (client.py)
- ✅ Implemented validation logic (validator.py)
- ✅ Added `requests>=2.31.0` to requirements.txt

### Session 2-3: Integration
- ✅ Updated Conversation model with template fields
- ✅ Enhanced callbacks.py with:
  - Template API integration
  - Script validation
  - Dynamic keyboard building
  - Strict/flexible enforcement
- ✅ Updated text.py to use API-driven templates
- ✅ Added TEMPLATE_API_URL to .env.example
- ✅ Created comprehensive test suite (15 tests)

### Commit History
```
8d14fdb feat(templates): Session 3 Final - Config and tests
9dc28df feat(templates): Session 2-3 - Handler integration with validation
5b11119 feat(templates): Session 1 - template module foundation
```

---

## 🚀 Deployment Steps

### Step 1: Push Development Branch

```bash
cd /Users/user/Documents/BLAS/PRODUCTION/DIALECT_BOT_TERRAFORM_AWS_V1/editorbot-stack/editorBot
git push origin Development
```

### Step 2: Update Environment Variables on EC2

SSH to EC2 instance and add template API URL:

```bash
# Connect via SSM (recommended)
aws ssm start-session --target i-013b229ba83c93cb9

# Or SSH directly
ssh ubuntu@18.198.2.201

# Add environment variable
cd /home/ubuntu/editorbot
echo 'TEMPLATE_API_URL=https://qcol9gunw4.execute-api.eu-central-1.amazonaws.com' >> .env

# Verify
cat .env | grep TEMPLATE
```

### Step 3: Pull Latest Code on EC2

```bash
cd /home/ubuntu/editorbot
git fetch origin
git checkout Development
git pull origin Development

# Update submodules if needed
git submodule update --init --recursive
```

### Step 4: Rebuild Docker Container

```bash
cd /home/ubuntu/editorbot

# Stop current container
docker compose down

# Rebuild with new dependencies
docker compose build --no-cache

# Start with new code
docker compose up -d

# Verify logs
docker compose logs -f editorbot
```

### Step 5: Verify Deployment

#### Test API Connectivity
```bash
docker exec editorbot-editorbot-1 python3 -c "
from bot.templates.client import TemplateClient
client = TemplateClient()
templates = client.list_templates()
print(f'✅ Fetched {len(templates)} templates')
for t in templates:
    print(f'  - {t[\"name\"]} ({t[\"id\"]})')
"
```

Expected output:
```
✅ Fetched 3 templates
  - Opinion Monologue (opinion_monologue_reel)
  - Explainer Slides (explainer_slides)
  - Narrated Thought (narrated_thought_horizontal)
```

#### Test Validation Logic
```bash
docker exec editorbot-editorbot-1 python3 /app/test_template_module.py
```

Expected output:
```
==================================================
✅ ALL TESTS PASSED - Template module is ready!
==================================================
```

#### Test with Telegram Bot
1. Send voice message to bot
2. Progress through: transcript → mediation → script → confirm
3. Verify template selection appears with dynamic buttons
4. Select a template
5. Verify validation runs (check logs)
6. Verify soundtrack selection appears

---

## 🔍 Monitoring & Troubleshooting

### View Bot Logs
```bash
# Real-time logs
docker compose logs -f editorbot

# Filter for template activity
docker compose logs editorbot | grep -i template

# Filter for validation
docker compose logs editorbot | grep -i validation
```

### CloudWatch Logs (Lambda API)
```bash
# View Lambda logs
aws logs tail /aws/lambda/template-config-api --follow --region eu-central-1

# Filter for errors
aws logs filter-pattern /aws/lambda/template-config-api --pattern "ERROR" --region eu-central-1
```

### Common Issues

#### Issue: "No module named 'requests'"
**Solution:** Rebuild Docker image
```bash
docker compose build --no-cache
docker compose up -d
```

#### Issue: "Error fetching templates"
**Diagnosis:**
```bash
# Check API endpoint
curl https://qcol9gunw4.execute-api.eu-central-1.amazonaws.com/templates

# Check from inside container
docker exec editorbot-editorbot-1 curl https://qcol9gunw4.execute-api.eu-central-1.amazonaws.com/templates
```

**Solution:** Verify Lambda API is running (see Terraform outputs)

#### Issue: "Template validation always fails"
**Diagnosis:**
```bash
# Check script structure
docker exec editorbot-editorbot-1 python3 -c "
from bot.state.runtime import get_conversation
convo = get_conversation(YOUR_CHAT_ID)
print(convo.final_script)
"
```

**Solution:** Ensure script has proper structure (total_duration, structure_type, beats)

#### Issue: "Template buttons don't appear"
**Check:**
1. TEMPLATE_API_URL environment variable set
2. API returns templates (see curl test above)
3. Bot logs show "✅ Guion final confirmado"

---

## 🧪 Testing Checklist

### Unit Tests (Local)
- [ ] Run `python3 test_template_module.py` - passes
- [ ] Run `pytest tests/test_template_integration.py -v` - all pass

### Integration Tests (On EC2)
- [ ] API connectivity test passes
- [ ] Template list fetched successfully
- [ ] Validation test passes

### End-to-End Tests (Telegram Bot)
- [ ] Voice → transcript → mediation workflow
- [ ] Script generation and confirmation
- [ ] Template selection displays (dynamic buttons)
- [ ] Template selection triggers validation
- [ ] Valid script: proceeds to soundtrack
- [ ] Invalid script (strict): shows error and options
- [ ] Invalid script (flexible): shows warning + allows continue
- [ ] Soundtrack selection works
- [ ] Conversation state persists correctly

---

## 📊 Performance Considerations

### API Call Optimization
- Templates cached in Conversation.template_spec after first fetch
- List fetched once per user session
- Full spec fetched only when user selects template

### Failure Modes
- API unavailable: Bot shows error, user can retry
- Validation fails (strict): User can edit script or choose different template
- Validation warning (flexible): User can proceed or edit

---

## 🔄 Rollback Plan

If issues arise:

```bash
# On EC2
cd /home/ubuntu/editorbot
git checkout main
docker compose down
docker compose build
docker compose up -d
```

To disable templates without rollback:
```bash
# Comment out template imports in handlers
# Bot will skip template selection and go directly to render
```

---

## 📝 Next Steps (Future)

### Phase 3 (Optional Enhancements)
- [ ] Add template caching (Redis or in-memory)
- [ ] Add template analytics (usage tracking)
- [ ] Create template creation UI
- [ ] Add template versioning

### Phase 4 (Advanced)
- [ ] Multi-language template support
- [ ] User-uploaded custom templates
- [ ] A/B testing framework
- [ ] Advanced validation rules (content analysis)

---

## 🔗 References

- **Lambda API Endpoint:** https://qcol9gunw4.execute-api.eu-central-1.amazonaws.com
- **Templates S3 Bucket:** bot-templates-20260121100906067300000001
- **EC2 Instance:** i-013b229ba83c93cb9 (18.198.2.201)
- **Implementation Plan:** [TEMPLATE_INTEGRATION_PLAN.md](../../content-pipeline-docs/TEMPLATE_INTEGRATION_PLAN.md)
- **Template Specs:** [aws-content-pipeline/templates/](../../aws-content-pipeline/templates/)

---

**Deployment Owner:** Development Team  
**Last Updated:** 21 January 2026  
**Status:** ✅ Ready for Production Deployment
