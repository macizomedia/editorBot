# Template Integration Deployment Guide

**Date:** 21 January 2026
**Branch:** Development
**Status:** Ready for EC2 Deployment
**Deployment Method:** 🤖 Automated via GitHub Actions

---

## ⚠️ SECURITY NOTICE

This project uses **automated deployment via GitHub Actions** with AWS SSM (Systems Manager).

**✅ DO:**
- Deploy by merging to `main` branch (triggers GitHub Actions)
- Use SSM Session Manager for manual access (no SSH keys)
- Monitor deployments via GitHub Actions UI

**❌ DON'T:**
- Manually SSH to EC2 and run git pull
- Expose SSH keys or use direct SSH access
- Run docker commands manually on EC2

**Why?** The GitHub Actions workflow:
- Uses SSM (no exposed SSH ports)
- Has proper error handling and rollback
- Logs all actions to CloudWatch
- Updates submodules correctly
- Validates deployment health

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

## 🚀 Deployment Steps (Automated via GitHub Actions)

### ⚠️ IMPORTANT: Use Automated Deployment

**DO NOT deploy manually via SSH.** This project has a GitHub Actions workflow that handles deployment safely via AWS SSM.

### Prerequisites

Ensure these GitHub Secrets are configured in `editorbot-stack` repository:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION` (eu-central-1)
- `EDITORBOT_INSTANCE_ID` (EC2 instance ID for the control VM)
- `TOKEN_DEPLOY` (GitHub PAT for submodule access)

### Step 1: Set Runtime Secrets (One-time Setup)

Before first deployment, store secrets in SSM Parameter Store (recommended):

```bash
aws ssm put-parameter --name "/editorbot/telegram_bot_token" --type "SecureString" --value "<TELEGRAM_BOT_TOKEN>" --overwrite --region eu-central-1
aws ssm put-parameter --name "/editorbot/gemini_api_key" --type "SecureString" --value "<GEMINI_API_KEY>" --overwrite --region eu-central-1
aws ssm put-parameter --name "/editorbot/template_api_url" --type "SecureString" --value "<TEMPLATE_API_URL>" --overwrite --region eu-central-1
aws ssm put-parameter --name "/content-pipeline/content_bucket_name" --type "SecureString" --value "<CONTENT_BUCKET_NAME>" --overwrite --region eu-central-1

Note: If Terraform appends a random suffix to the content bucket name, set
`/content-pipeline/content_bucket_name` after the first apply using the actual
bucket name it creates.
```

### Step 2: Merge Development → Main (Triggers Deployment)

**Option A: Via Pull Request (Recommended)**

1. Go to: https://github.com/macizomedia/editorBot/pull/new/Development
2. Create Pull Request: `Development` → `main`
3. Review changes
4. Merge PR

**Option B: Direct Merge (Fast)**

```bash
# In editorBot submodule
cd /Users/user/Documents/BLAS/PRODUCTION/DIALECT_BOT_TERRAFORM_AWS_V1/editorbot-stack/editorBot
git checkout main
git pull origin main
git merge Development
git push origin main

# In parent editorbot-stack repo
cd /Users/user/Documents/BLAS/PRODUCTION/DIALECT_BOT_TERRAFORM_AWS_V1/editorbot-stack
git add editorBot
git commit -m "chore: update editorBot submodule with template integration"
git push origin main
```

### Step 3: Monitor GitHub Actions Deployment

1. Go to: https://github.com/macizomedia/editorbot-stack/actions
2. Watch the `deploy` workflow run
3. Workflow will automatically:
   - Pull latest code on EC2 via SSM
   - Update submodules (including editorBot)
   - Rebuild Docker container
   - Start services
   - Verify health

**Deployment takes ~5 minutes**

### Step 4: Verify Deployment via CloudWatch

Monitor SSM command execution:

```bash
# Get latest command ID from GitHub Actions output
COMMAND_ID="<from-github-actions>"

# View execution status
aws ssm list-command-invocations \
  --command-id "$COMMAND_ID" \
  --details \
  --region eu-central-1

# View logs
aws logs tail /content-pipeline/editorbot --follow --region eu-central-1
```

### Step 5: Verify Deployment (Post-Deployment Tests)

Once GitHub Actions completes, verify the deployment:

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
curl <TEMPLATE_API_URL>/templates

# Check from inside container
docker exec editorbot-editorbot-1 curl <TEMPLATE_API_URL>/templates
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

If issues arise after deployment:

**Option 1: Via GitHub Actions (Recommended)**
```bash
# Revert the merge commit in editorbot-stack
cd /Users/user/Documents/BLAS/PRODUCTION/DIALECT_BOT_TERRAFORM_AWS_V1/editorbot-stack
git revert HEAD
git push origin main

# GitHub Actions will automatically deploy the reverted version
```

**Option 2: Manual Rollback (Emergency Only)**
```bash
# Connect via SSM
aws ssm start-session --target <EDITORBOT_INSTANCE_ID> --region eu-central-1

# On EC2
cd /home/ubuntu/editorbot
git reset --hard <previous-commit-sha>
git submodule update --recursive
docker compose down
docker compose up -d --build
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

- **Lambda API Endpoint:** <TEMPLATE_API_URL>
- **Templates S3 Bucket:** bot-templates-20260121100906067300000001
- **EC2 Instance:** <EDITORBOT_INSTANCE_ID> (control VM)
- **Implementation Plan:** [TEMPLATE_INTEGRATION_PLAN.md](../../content-pipeline-docs/TEMPLATE_INTEGRATION_PLAN.md)
- **Template Specs:** [aws-content-pipeline/templates/](../../aws-content-pipeline/templates/)

---

**Deployment Owner:** Development Team
**Last Updated:** 21 January 2026
**Status:** ✅ Ready for Production Deployment
