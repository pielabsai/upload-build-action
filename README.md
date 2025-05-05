# Pie Build Uploader GitHub Action

This GitHub Action automates the process of uploading iOS and Android app builds (APP, APK, AAB) to Pie's platform. It supports single file uploads as well as directory uploads (which will be automatically zipped).

## Features

- Supports iOS (APP) and Android (APK, AAB) build files
- Automatic ZIP creation for directory uploads
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
    build_path: path/to/your/build.app  # or .apk, .aab
```

## Inputs

| Input | Description | Required |
|-------|-------------|----------|
| `pie_api_key` | Your Pie API key for authentication. Should be stored as a GitHub secret. | Yes |
| `build_path` | Path to your build file (APP, APK, or AAB) or directory. If a directory is provided, it will be automatically zipped. | Yes |

## Supported File Types

- `.app` - iOS application builds
- `.apk` - Android application builds
- `.aab` - Android App Bundle
- `.zip` - Automatically created for directory uploads

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

## Directory Upload Example
```yaml
- name: Upload Build Directory
  uses:pielabsai/upload-build-action@v1.2
  with:
    pie_api_key: ${{ secrets.PIE_API_KEY }}
    build_path: build/artifacts  # Directory will be automatically zipped
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
