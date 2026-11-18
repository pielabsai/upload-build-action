# Pie Build Uploader GitHub Action

This GitHub Action uploads iOS Simulator APP and Android APK builds to Pie. It supports single file uploads as well as iOS Simulator `.app` directory uploads (which will be automatically zipped). Android App Bundles (`.aab`) are unsupported; upload an `.apk` instead.

## Features

- Supports iOS Simulator (APP) and Android (APK) build files
- Automatic ZIP creation for iOS Simulator `.app` directories
- Secure API key authentication
- Built-in file validation and error handling
- Simple integration with existing GitHub workflows

## Prerequisites

Before using this action, you'll need:
1. A Pie account - Sign up at [https://app.pie.inc](https://app.pie.inc)
2. A Pie API key - After signing up, you can generate your API key for your app.

## Usage

To use this action in your GitHub workflow, add the following step to your `.github/workflows/your-workflow.yml` file:

```yaml
- name: Upload Build to Pie
  uses: pielabsai/upload-build-action@v1.2  # Replace with actual repository/version
  with:
    pie_api_key: ${{ secrets.PIE_API_KEY }}
    build_path: path/to/your/build.app  # or .apk
```

## Inputs

| Input | Description | Required |
|-------|-------------|----------|
| `pie_api_key` | Your Pie API key for authentication. Should be stored as a GitHub secret. | Yes |
| `build_path` | Path to your iOS Simulator APP, Android APK, or ZIP containing a supported build. APP directories are automatically zipped. | Yes |
| `pr_number` | Pull request number. When set, Pie tests this build on that pull request and comments the results there. See [Test a pull request's build](#test-a-pull-requests-build). | No |
| `commit_sha` | Full commit SHA the build was made from. Used only with `pr_number`. Defaults to the pull request's head commit, or the workflow's commit for manual runs. | No |
| `repository` | `owner/name` of the pull request's repository. Used only with `pr_number`. Defaults to the current repository. | No |

## Outputs

| Output | Description |
|--------|-------------|
| `build_id` | The `buildID` returned by the Pie API. Pass this to subsequent steps (e.g. when calling the `run_tests_on_target` MCP tool or `POST /v1/runs/custom`) to identify the build you just uploaded. |

### Using the `build_id` output

```yaml
- name: Upload build
  id: pie_upload
  uses: pielabsai/upload-build-action@v1.3
  with:
    pie_api_key: ${{ secrets.PIE_API_KEY }}
    build_path: build/MyApp.app

- name: Kick off tests against the new build
  env:
    PIE_API_KEY: ${{ secrets.PIE_API_KEY }}
    BUILD_ID: ${{ steps.pie_upload.outputs.build_id }}
  run: |
    curl -X POST https://api.pie.inc/v1/runs/custom \
      -H "X-API-Key: $PIE_API_KEY" \
      -H "Content-Type: application/json" \
      -d "{
        \"buildID\": \"$BUILD_ID\",
        \"existingTCIDs\": [368930, 488349],
        \"newTCPrompts\": [\"Smoke test the login flow on the new build\"]
      }"
```

## Test a pull request's build

Pass `pr_number` and Pie tests that exact build on the pull request, then comments on it with the tests it ran, their results and videos. Pull requests that don't upload a build get no run and no comment, so you choose which pull requests Pie tests.

Before you start, ask Pie to connect your Pie app to the repository with pull request testing on. Automatic runs on every pull request stay off unless you ask for them.

This workflow runs only when someone adds the `pie-test` label to a pull request, or starts it by hand from the Actions tab:

```yaml
name: Pie PR test
on:
  pull_request:
    types: [labeled]
  workflow_dispatch:
    inputs:
      pr_number:
        description: Pull request number to test
        required: true

jobs:
  pie:
    if: github.event_name == 'workflow_dispatch' || github.event.label.name == 'pie-test'
    runs-on: macos-latest  # ubuntu-latest is enough for Android
    steps:
      - uses: actions/checkout@v4

      # Build an iOS Simulator .app or an Android debug .apk here

      - name: Send the PR build to Pie
        uses: pielabsai/upload-build-action@v1.5
        with:
          pie_api_key: ${{ secrets.PIE_API_KEY }}
          build_path: build/Build/Products/Debug-iphonesimulator/MyApp.app  # or app/build/outputs/apk/debug/app-debug.apk
          pr_number: ${{ github.event.pull_request.number || inputs.pr_number }}
```

Things to know:

- **Manual runs:** in "Run workflow", pick the pull request's branch. The build and `commit_sha` come from that branch, and Pie checks the commit is the pull request's latest.
- **Testing again:** Pie runs once per pull request and commit. Uploading the same commit again succeeds and returns the same `build_id` without a second run. Push a new commit, then remove and re-add the label.
- **Forks:** GitHub does not give secrets to workflows from forked pull requests, so this works for branches in your own repository.

## Supported File Types

- `.app` - iOS Simulator application builds
- `.apk` - Android application builds
- `.zip` - An APK or iOS Simulator `.app` at the archive root; automatically created for iOS Simulator `.app` directory uploads

An `.aab` filename is rejected before upload, including uppercase extensions. Renaming or wrapping a bundle in a ZIP does not make it a supported build. A ZIP upload is checked asynchronously by Pie; a successful upload response does not mean the build passed verification.

## Example Workflows

### iOS Build Upload
```yaml
name: Upload iOS Build
on:
  push:
    tags:
      - 'v*'

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      # Your iOS build steps here
      
      - name: Upload to Pie
        uses: pielabsai/upload-build-action@v1.2
        with:
          pie_api_key: ${{ secrets.PIE_API_KEY }}
          build_path: build/MyApp.app
```

### Android Build Upload
```yaml
name: Upload Android Build
on:
  push:
    tags:
      - 'v*'

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      # Your Android build steps here
      
      - name: Upload to Pie
        uses: pielabsai/upload-build-action@v1.2
        with:
          pie_api_key: ${{ secrets.PIE_API_KEY }}
          build_path: app/build/outputs/apk/release/app-release.apk
```

## iOS Simulator Directory Upload Example
```yaml
- name: Upload Build Directory
  uses:pielabsai/upload-build-action@v1.2
  with:
    pie_api_key: ${{ secrets.PIE_API_KEY }}
    build_path: build/MyApp.app  # APP directory will be at the ZIP root
```

## Trigger Strategies

Here are several ways you can trigger the build upload action:

### 1. On Release or Tag Creation
```yaml
name: Upload Build on Release
on:
  release:
    types: [published]
  # Or use tags
  # push:
  #   tags:
  #     - 'v*'  # Matches v1.0, v20.15.10, etc.

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      # Build steps here
      - name: Upload to Pie
        uses: pielabsai/upload-build-action@v1.2
        with:
          pie_api_key: ${{ secrets.PIE_API_KEY }}
          build_path: path/to/your/build.app
```

### 2. Scheduled Uploads
```yaml
name: Scheduled Build Upload
on:
  schedule:
    # Daily at 00:00 UTC
    - cron: '0 0 * * *'
    # Or weekly on Sunday
    # - cron: '0 0 * * 0'

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      # Build steps here
      - name: Upload to Pie
        uses: pielabsai/upload-build-action@v1.2
        with:
          pie_api_key: ${{ secrets.PIE_API_KEY }}
          build_path: path/to/your/build.app
```

### 3. Manual Trigger
```yaml
name: Manual Build Upload
on:
  workflow_dispatch:  # Allows manual triggers from GitHub UI
    inputs:
      build_type:
        description: 'Type of build to upload (ios/android)'
        required: true
        default: 'ios'

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      # Build steps here
      - name: Upload to Pie
        uses: pielabsai/upload-build-action@v1.2
        with:
          pie_api_key: ${{ secrets.PIE_API_KEY }}
          build_path: ${{ github.event.inputs.build_type == 'ios' && 'path/to/ios/build.app' || 'path/to/android/build.apk' }}
```

### 4. On Pull Request (for Testing)
```yaml
name: Test Build Upload
on:
  pull_request:
    branches: [ main, develop ]
    types: [ closed ]
    paths:
      - 'app/**'  # Only trigger on app code changes

jobs:
  upload:
    if: github.event.pull_request.merged == true  # Only run if PR was merged
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      # Build steps here
      - name: Upload to Pie
        uses: pielabsai/upload-build-action@v1.2
        with:
          pie_api_key: ${{ secrets.PIE_API_KEY }}
          build_path: path/to/your/build.app
```

### Best Practices for Triggers

1. **Release-based uploads**: Best for production builds when you want to ensure only stable versions are uploaded
2. **Scheduled uploads**: Useful for nightly or weekly builds to track progress
3. **Manual triggers**: Helpful for ad-hoc testing or when you need control over when builds are uploaded
4. **PR-based uploads**: Good for testing builds before merging into main branches

## Error Handling

The action includes built-in error handling for common scenarios:
- Missing build file
- Unsupported file types
- API authentication failures
- Upload failures

Any errors will cause the action to fail with an appropriate error message.

## Security Notes

- Always store your Pie API key as a GitHub secret
- Never commit API keys directly in your workflow files
- The action automatically handles secure transmission of your build files

## Support

For issues, feature requests, or questions about this GitHub Action, please open an issue in the repository.

## License

This GitHub Action is available under the MIT License. See the LICENSE file for more details.
