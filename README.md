To manually trigger a build:
```
gcloud builds triggers run manual-claude-deployment-trigger --region=us-central1
gcloud builds submit --config cloudbuild.yaml
```

Recently added github integration with these commands in your chat:

"List my repos" - Shows your GitHub repositories
"Show file app.py from claude-app repo" - Gets a specific file from a repo
"What does this code do?" (after showing a file) - Claude will analyze the code

To get the current url:
gcloud run services describe claude-chat-app --region=us-central1 --format='value(status.url)'

