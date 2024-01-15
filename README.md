# Táblaexport (Table export)

This is a concept project that uses an online Excel file (published in SharePoint by a university) as its database and turns it into an easily navigable webpage for students to use. It can follow course codes (so if changes happen in the database, it automatically updates your calendar), or you can select which subjects/entries you want to export to your calendar. Originally the project used the MS Office API to retrieve data from SharePoint, but later this had to be changed to utilizea a PowerApps Flow, and an email server as a relay.

Please note that this code probably won't work with your SharePoint system - mainly because it isn't designed to do so. This was both an experiment and a proof-of-concept project.

Other (notable) packages used:
 - Flask (web framework)
 - icalendar (exporting the calendar to .ical format)
 - imaplib (to retrieve the Excel file from the server)
 - openpyxl (reading the Excel file)
