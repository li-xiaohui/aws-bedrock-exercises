# Bedrock CLI Commands

Set your region once, then reuse across all commands:

```bash
export REGION=us-east-1
# export REGION=ap-southeast-1
```

## List inference profiles (filter for Sonnet 4)

```bash
aws bedrock list-inference-profiles \
  --region "$REGION" \
  --query "inferenceProfileSummaries[?contains(inferenceProfileName, 'Sonnet 4') || contains(inferenceProfileId, 'sonnet-4')].[inferenceProfileId,inferenceProfileName]" \
  --output table
```

## List latest models by provider

Set the provider, then run the command:

```bash
export PROVIDER=Anthropic
# export PROVIDER=OpenAI
# export PROVIDER=DeepSeek
# export PROVIDER="Moonshot AI"

aws bedrock list-foundation-models \
  --region "$REGION" \
  --by-provider "$PROVIDER" \
  --query "modelSummaries[*].[modelId,modelName]" \
  --output table
```
