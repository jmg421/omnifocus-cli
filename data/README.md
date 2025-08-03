# Data Directory

This directory is used by OFCLI for local data storage and caching.

## Structure

- `examples/` - Sample data files showing expected JSON formats
- `omnifocus.sqlite` - Local SQLite database for advanced querying (created automatically)


## Usage

When you run OFCLI commands, the application will automatically create necessary files in this directory. The examples folder shows the expected format for OmniFocus export data.

## Privacy

**Important**: This directory may contain personal task data when OFCLI is in use. The `.gitignore` file is configured to prevent accidental commit of personal data files.

## Sample Data

See `examples/sample_tasks.json` for an example of the OmniFocus export format that OFCLI expects. 