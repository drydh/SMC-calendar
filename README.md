# SMC-calendar

Scripts for extracting **Polopoly calendar entries** from the SMC web page and
to compile a weekly digest email.

## Requirements and installation

- Python (3.7+)
- Package dependencies listed in `requirements.txt`: to install dependencies, run
```$ python3 -m pip install -r requirements.txt```
- KTH account with access to edit Polopoly and send emails: copy/rename `config.default` to `config` and add  the username to send the emails from

## Contents

1. Python script `semads.py` (which uses `smc_scraper.py` and `utility.py`) to retrieve calendar entries.
2. Python script `seminarmailer.py` to send out the digest email.
3. Bash script `calendar.sh` to facilitate the previous two steps.
4. Python script `iml_scraper.py` to retrieve calendar entries from the web page of Insitut Mittag-Leffler, which can be run separately as a helper script if those entries should be added to the calendar.
5. Bash script `convert-tex-to-polopoly.sh` to convert simple TeX code to Polopoly html source.
6. Bash script configuration defaults `config.default`, to be copied and customized (probably just the username).

## General workflow

1. Add calendar entries to [Polopoly](https://www-edit.sys.kth.se/polopoly/CM) (Externa sajter -> Stockholms Matematikcentrum -> Calendar)
    - Entries from e-mails to `kalendarium@math-stockholm.se`.
       - Possibly entries from [SU calendar](https://math.su.se) or general SU-emails (e.g., bachelor/master theses presentations, docent lectures, ...) that would be suitable for the calendar.
       - Some seminar organizers add entries directly into Polopoly themselves.
       - See [Polopoly instructions](#polopoly-instructions) below for more information.

    - Entries from Mittag-Leffler
       - run `iml_scraper.py` or `iml_scraper.py > output.txt`

2. Add/remove subscriptions to emails.txt
    - Requests come to `kalendarium@math-stockholm.se`.
    - Lines starting with `#` are ignored.
    - Add expiry date (format: `YYYY-MM-DD`) after email (and a space) if the subscription is supposed to be temporary

3. Generate the calendar email (`semads.py`)
4. Possibly do minor edits
     - Potential problem: multi-day conferences
     - PhD defenses without lecturer in title (script `semads.py` could be improved to include this)
5. Send the calendar email (`seminarmailer.py`)

Bash script `calendar.sh` facilitates steps 3-5. See [Usage](#usage).

## Usage

1. Make sure `calendar.sh`, `semads.py` and `seminarmailer.py` are in the same directory.
2. Update `"user"` in `calendar.sh` file to reflect your KTH username.
3. Update `"python"` in `calendar.sh` file if necessary.
4. Make sure that the `calendar.sh` file is executable (e.g. use `chmod +x calendar.sh`).
5. Run `./calendar.sh` from the directory containing the files.
6. The script will create the week's email and display it in `nano` editor.
7. Check the email and press `ctrl+o` to save any changes.
8. When the email has been checked press `ctrl+x`.
9. Press `y` to send the email or `ctrl+c` to exit.
10. When prompted, enter your KTH password to send the email.

Notes:

- You can run these files from any computer.
- If you are running these files from your own computer there is an option to use a socks proxy for the mailer. [currently disabled]

## Polopoly instructions

- URL: [https://www-edit.sys.kth.se/polopoly](https://www-edit.sys.kth.se/polopoly)
- [Documentation](https://intra.kth.se/en/administration/kommunikation/webb/verktyg/polopoly)

- Format of calendar ads:
  - Title "First Last: Title"
  - Date
  - Place (physical or Zoom)
  - Video link (if both physical and Zoom)
  - Lecturer "First Last (University)" [NOT used for thesis defenses]
  - Contents "Abstract: ABSTRACT"
- For master presentation / thesis defense:
  - Choose type under "Seminar specifics"
  - Enter respondent under "Seminar specifics" (leave lecturer blank)
  - Enter supervisor under "Seminar specifics"

Notes:

- It can take a few minutes before changes in PoloPoly are reflected on the webpages.
- ID's, linking of pages, parents, copy & paste, ...
- When copying an article, hyperlinks are not copied but links to the same object, that is, changes in the hyperlink in the copied article also results in changes to the original.  Thus, should delete hyperlink and then add a new one. (typical scenario: DiVA-link in licentiate seminars / dissertations)
- Language settings ...
- Repair link if inserting article in different folder (typically: new year)
