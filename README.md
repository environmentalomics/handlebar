# Handlebar

## Introduction

Handlebar is a database for tracking your barcoded samples.  If you are going to be adding information to an existing database then you must at least be familiar with the material in this introductory section.  The web interface is designed to be largely self-documenting, so once you understand the basic operation of the system you can just go ahead and try it out.

NOTE: As with any database, one of the most important aspects is making sure that the data entered is consistent and complete.  The database will do some basic checking of the information you submit, but it is vital that you are familiar with the conventions and standards for the items you are labelling.  These will be specific to the different groups and different sample types, so they are outside the scope of this document.  Such usage information can be stored as comments in the database and viewed via the website - see the section '''barcode types''' below for more details.

## Basic Principles

The fundamental principle of the online database is that stored items are given a unique number, and that information relating to the sample is entered into a spreadsheet against that number.  The database then ingests this information so that it can be shared by multiple users, and across multiple sites.  As all the sample information related to a project accumulates, searching and reporting is possible.  Once a project is completed, sets of sample data can be published - that is, the information on the codes is made publicly available.

The online database is not dependent on the use of any specific barcoding hardware.  It is perfectly possibly, though tedious, to hand-write the code numbers onto the stored samples.  Any printing system capable of outputting numbered codes is suitable for use with the barcode database, but we do support a standard set of hardware and this is detailed below.

## Barcode Blocks, Users and Barcode Types

Barcodes are allocated by the system in blocks of up to 1000.  The reason for the allocation step is to make sure that all code numbers are unique over different sites.  Allocating a block of codes does not mean that you have to actaully use any or all of them.  It simply means they are available for use.  When you download a spreadsheet from the system to edit the information, you will download a block at a time.

The database knows about users of the system.  Each user is identified by a short username, and each barcode block is owned by one user.

The database also knows about various types of things which may be barcoded.  The type associated with a barcode determines what fields will be available in the spreadsheet when you come to enter data. Each barcode block is given a type at the time of allocation.

## Barcode Lifecycle

The lifecycle of a barcode in the system is as follows:

1. Anything higher than the current highest allocated number is a potential barcode, waiting to be claimed by a user.
1. When a barcode is allocated it becomes associated with a user and an item type as part of an allocation block.  At this point no other information is entered, and the barcode may never actually be used.  It is simply available for use.
1. The system knows the barcode has been used when data about it is uploaded (via a spreadsheet CSV file).
1. The barcode information may be updated by editing and re-uploading the CSV.
1. If the item is destroyed then barcode can marked disposed in the database.  After this it can no longer be updated.

* It is also possibly, though not necessary, to dispose an allocated but unused barcode.  This simply tells the database that the code will never be used.

Importantly, a code cannot go backwards (eg. once a code is allocated it cannot be de-allocated, once disposed it cannot be reinstated) without intervention by the database administrator.

The database can also be thought of as having a lifecycle:

1. Development phase, where type definitions are being added and tested.  This will be done within a test database setup.
1. Active phase, where users are storing samples and adding information.
1. Archive phase, where the information is archived and no longer updated.  Ranges of barcodes can be selected for publication and the information will be made available via EnvBase.

## Security and User Names

Usernames are not password protected, as it is assumed that everyone who is given access to the system can be trusted. Once you have access to the system you can impersonate any other user, but obviously you should only do this if you are entering data on their behalf.  In order to prevent you from accidentally changing another user's data you will always be asked to identify yourself before making any update on the system.

## Wasting Codes

Users should not think in terms of codes being 'wasted' if they are allocated but then never used.  Within reason, there is no shortage of numbers to go around even if only a fraction of them are actually used for labelling.  If, say, you think you may get up to 300 sediment samples over the course of two years, in batches of 50, then allocate yourself a block of 300 codes at the start, rather than 50 at a time.  You will probably find the system easier to use this way, as all your records will be together in one spreadsheet.

Wasting of physical labels is another matter, of course.  You can print or request these as you see fit.

## Breaking the Rules and Correcting Mistakes

The web interface intentionally limits what a user is able to do.  This is partly for the sake of simplicity and partly to maintain the integrity of the data within the database.  An admin_barcodes.cgi module is provided for when you need to make changes outside the normal lifecyle.  The system administrator can configure which features are available in this interface.

## Getting Started

To access the website you will need to know the URL and password for the database you are using.  Once you have read the above section and been given access to the website you are ready to use the system.  You must first register your user name, giving your real name and your institution.  The user name should be short and contain only lowercase letters and numbers.  I simply use my regular login name, ie. 'tbooth'.

You need to decide what type of thing you want to barcode and how many barcodes you want to allocate in a block.  If none of the [[BarcodeItemTypes|existing types]] are suitable, then a new type must be added.  The fields for the new type need to be considered carefully, and the description needs to be added to the database by the system administrator.

In addition to a computer with an internet connection and a web browser you also need a spreadsheet program to edit the CSV files with the data in.  OpenOffice.org Calc is the preferred spreadsheet, and helper macros are avaialbel for it (see below).  Excel, Gnumeric and any other spreadsheet capable of loading CSV files will also work fine.

Follow the prompts on the site to download the CSV file, then upload it again when you have data to submit.

# Detailed Notes

## Code Allocations

The database currently issues 8-digit codes which are shown in the form 00-001234.  The 8-digit size is because this size of code fits neatly on the side of an Eppendorf tube, it is not a fundamental feature of the database; the format of the codes is controlled by the configuration file on the server.  The database will allocate codes according to the following rules:

1. The block must not be larger than the maximum size specified in the config.
1. If there are no codes in the database yet, the starting code will be taken from the config file.  By using a different offset for each database (eg 2000000 for the Fish Tox. codes) the codes are kept unique across all projects.
1. The highest allocated code will be determined, then 1 is added to this.  Finally the figure is rounded up to the nearest 100 (or whatever is set in the config file) and this becomes the base for the next allocation block.

Codes which slip between blocks will simply go unused.  Codes are allocated in strict order, and once the allocation is made the type and size of the block should not be changed (this can only be done by the database administrator in any case).

## Type Descriptions

Detailed information is given on the [[BarcodeItemTypes]] page.  In summary, to get a description of each type, click _Describe type_.  You will see a summary description and a table in which each row represents a heading in the spreadsheet.  Bold fields are compulsory, so if you enter any data at all for the barcode then you must fill in at least these columns.  The maximum size of the field is also given; for text fields this is the number of characters (blank for unlimited) and for numeric fields this is the number of bytes of storage, so an integer of size 4 can range from -2,147,483,648 to -2,147,483,647.  For floating point fields, the size determines the maximum precision available, rather than the size of the values.

## CSV Download, Data Upload and Validation

Once you have created a block of barcodes, you can download a CSV or XLS file to be loaded straight into a spreadsheet.  You will need to use the text import function and check that the separator is set to a comma and the text quotation is set to a double quote.  When you first load a CSV file for a new block of codes you will see the codes down the left hand column and the headings at the top.

Enter the details of the samples into the spreadsheet, referring to the type description to see what values are expected in each column and which fields are compulsory, then upload the data back to the site.  The input will be validated against the database, and only if every row validates correctly will the data be uploaded.  If any validation fails then no changes will be made in the database at all, and an error report will be shown.  You should try to correct the problem and re-submit the file.

Typical problems are:

* You have not filled in a compulsory field.
* You have put text in a numeric field.
* A text entry is too long.
* A value in a date column cannot be interpreted.  The recommended format for dates is to say, eg. '12 Jan 2005'.  Dates in the form '12/01/2005' should be avoided as they are ambiguous - many people have their spreadsheets set to the default American style mm/dd/yyyy ordering.
* There is some extra data in the file which cannot be processed.

Some notes on the validation process:

* You can re-order the rows and columns in the spreadsheet, and the database will deal with this.
* You do not have to use the whole block at once, nor do you have to use up the codes in order.
* You can delete rows you are not using from the spreadsheet, and just upload a subset of the block.
* But you cannot combine two blocks into one spreadsheet and upload the whole lot at once.
* If a row in the spreadsheet contains just a barcode, and the barcode is unused it will be skipped.
* But if the row contains just a barcode and there is data for that code already in the database an error will be triggered.
* You can have blank rows in the spreadsheet, but if you put data in any cell outside the barcode data area then this will trigger an error.
* Sometimes you may see a validation error which is propogated from the underlying database.  The wording of these can be a little technical, but it is not possible to translate every database error.

You can re-request and re-submit the spreadsheet file as often as you like.

## Disposing Code

Disposing a code indicates that you have physically destroyed the sample in question.  Disposing the code lets people know that the sample is no longer available and also removes the codes from the CSV download.  The code will no longer show in the tally of codes owned by the user.  Once a whole block has been disposed the entire block will be hidden in the admin interface.  You can also dispose codes which are still unused - this is only really useful if you want to dispose of an entire block where some codes are unused.

You can give a reason for disposal in the comments box.  The date of disposal will be automatically recorded.  The data for a disposed code will be preserved and can no longer be changed.  You can still query on a disposed code via the query interface and there will be a message indicating that the sample no longer exists, along with the last data logged.

You can dispose of whole ranges of codes at once by using colon-separated ranges.  For example to get rid of codes 120, 121, 122 and 140 you could enter into the box:

 120:122
 140

Please be careful when doing this that you do not dispose of more than you meant to.

## User Names and Validation

There is a configuration option which controls if strict username checking is enabled on the site.  As stated before, the system will believe that you are any user you claim to be.  The point of prompting for a user name is to stop one user unwittingly altering or disposing codes belonging to another.  If strict username checking is turned off, users will be able to dispose of codes and upload data without giving a user name first.

## The Query Interface

The current query interface supports basic queries or full reports (via GenQuery).  Enter a barcode (with or without the hyphen character) to see a summary of data.  Or select a report from the menus.

## The Printing Interface

If you want to make labels for your samples, you can mail the sire maintainer to request some or print them on your own printer.  The web interface can help you in two ways:

1. By generating an EPL file which you can feed directly to a Zebra barcode printer.
1. By generating a standard e-mail which goes off to the sire maintainer.

The web interface will validate the codes against the database, and will insist that codes are allocated to you before you print or request them.  The printing interface is there for convenience only; if you want to make use of the software supplied with the printer to design your own labels then go ahead.  Note that the website does not control the printer directly, it just generates a suitable EPL data file for you to print yourself.  You will see on-screen instructions for how to do this.

