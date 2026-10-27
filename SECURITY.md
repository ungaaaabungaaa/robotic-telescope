# Security

The application is offline. It accepts bounded local JSON, writes only new output directories, and has no web server, account, network client, device writer, or remote-control endpoint. Automatic astronomy-data and leap-second downloads are disabled. Request files must be regular, bounded, and not symbolic links; schemas, numeric ranges, target counts, and time grids are validated.

These checks do not sandbox arbitrary hostile files or the native scientific dependencies. Process files you trust, retain the recorded dependency set, and review updates. Custom reports contain the supplied site coordinates and target notes. Check them before sharing; precise private locations should not be included in a public report or issue.

For a vulnerability, use GitHub private vulnerability reporting if available. Otherwise open a minimal issue asking for a private contact without sensitive files or exploitation details. Physical telescope and solar-safety protection are outside this software's verified scope.
