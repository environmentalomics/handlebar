#!/usr/bin/perl
use strict; use warnings;

#All the standard CGI stuff...
use lib "..";
use barcodeUtil;
use Cache::FileCache;

#Somewhere to dump all my stuff
my $cache = new Cache::FileCache({namespace=>$0});

#If I can speed up the regeneration I may reinstate the cache expiration
# my $cache = new Cache::FileCache({namespace=>$0, default_expires_in=>"24 hours"});

our %CONFIG = %{bcgetconfig()};
our $CUSTOM_HEADER = $CONFIG{CUSTOM_HEADER};
our $SVNCLIENT = '/usr/bin/svn';
# our $SVNROOT = 'https://svn.sourceforge.net/svnroot/handlebar/templates';
our $SVNROOT = 'http://handlebar.svn.sourceforge.net/svnroot/handlebar/templates';
our $SVNBROWSE = 'http://handlebar.svn.sourceforge.net/viewvc/handlebar/templates';
# our $SVNDOWNLOAD = 'http://handlebar.svn.sourceforge.net/viewvc/*checkout*/handlebar/templates';

my $q = bcgetqueryobj;
my $title = "Public repository of Handlebar type templates";

#A way to force the cache to clear
my $forcereload = $q->param('forcereload');
$forcereload and $cache->clear();

#Heading stuff
print bcheader(), bcstarthtml($title),
      $q->div({-id=>"topbanner"}, customheader(), repo_navbanner(), bch1($title)),
      $q->start_div({-id=>"mainsection"}), "\n";

#The problem with accessing the SVN repository is that it is _SLOW_ :-(
#Therefore I will use a cache to remember the results.
#If the cache is out of date, I'll apologise to the user that this is going
#to take some time.
my @types;
my $types = $cache->get('TYPES');
if($types) { @types = @$types };

if(! @types)
{
	print $q->p("The cache of types is being regenerated.  Please be patient...");

	#get list of all the sql files
	#This is faster via viewvc, but that is liable to page once the number of files gets too
	#large.
	open my $svnfiles, "$SVNCLIENT ls $SVNROOT |" or die $!;
	@types = sort(grep(/.sql$/, <$svnfiles>));
	close $svnfiles;

	$cache->set(TYPES => \@types);
}

#Say what I got
print $q->h2("Showing details for ", scalar(@types), " types found in repository.");
print $q->start_ol();

#compile them with a download link and a browse history link
for(@types)
{
    chomp;
    #grab html (or put in an error)
    my ($typename) = /(.*).sql/;

    my $typedesc = $cache->get("$typename.html");
    if(!defined($typedesc))
    {
	#open my $typedesc_fh, "$SVNCLIENT cat $SVNROOT/$typename.html |" or die $!;
	open my $typedesc_fh, "wget -q -O - $SVNBROWSE/$typename.html |" or die $!;
	$typedesc = join('', <$typedesc_fh>) || '';
	close $typedesc_fh;
	#If nothing came back, save an empty string in the cache so we don't keep
	#hammering SVN.
    	$cache->set("$typename.html" => ($typedesc || ''));
    }

    #Print an index to the type - this means extracting the title summary.
    my ($title) = ($typedesc =~ /<h\d>([^<]+)<\/h\d>/);
    my ($summary) = ($typedesc =~ /<p>([^<]+)<\/p>/);
    $summary ||= '';
    $summary =~ s/\n.*//;
    if($title)
    {
	$summary = " - $summary" if $summary;
	print $q->li( $q->a( {-href => "#$typename" }, "<b>$title</b>") . $summary );
    }
    else
    {
	print $q->li( $q->a( {-href => "#$typename"},  "<i>$typename</i>" ));
    }
}
print $q->end_ol();

#Now actually print the types...
for(@types)
{
    chomp;
    my ($typename) = /(.*).sql/;

    my $typedesc = $cache->get("$typename.html");
    print $q->a( {-name => $typename}, '' );
    if($typedesc)
    {
	print $typedesc;
    }
    else
    {
	print $q->h2(bczapunderscores($typename)),
	      $q->p({-class=>'errorbox'}, 
		      "Error: An SQL template for this type was found, but there is no matching 
		      description in the repository database.");
    }

    #could grab meta-data (who, when added, last update, # of revs) but if people
    #really want to see this it is just one click away
    print $q->p( $q->a({-href => "$SVNBROWSE/$typename.sql"}, "Download SQL"), ' / ',
		 $q->a({-href => "$SVNBROWSE/$typename.sql?view=log"}, "View file history")
	       );

}

#add a form to submit types by asking for the .sql file and mailing it to me
#link to submit script here

print $q->h2("Adding or updating types"),
		$q->p("If you have defined your own type templates, you may use " .
			$q->a({-href=>'submit_a_type.cgi'}, "this form ") .
			"to submit them to the repository for others to use.");


print bcfooter();

#This function is cut-and-paste - it should be shared!
sub repo_navbanner
{
    my $res = '';

    #Equivalent of the internal navigation banner for the repository.
    my @sections = (
        { href=>"http://nebc.nerc.ac.uk/tools/handlebar", label=>"Handlebar home page" },
        { href=>"showtypes.cgi",   label=>"Browse templates" },
        { href=>"submit_a_type.cgi",   label=>"Submit a template" },
    );

    $sections[1]->{current} = 1;

    my $nbsp = sub{
      (my $foo = "@_") =~ s/ /&nbsp;/g;
      $foo;
    };

#   unless($barcodeUtil::divs_open)
#     {
#   $barcodeUtil::divs_open++;
#   $res .= $q->start_div({-id=>"topbanner"});
#     }

    $res .=
      $q->div( {-class=>'navbanner_outer'},
          $q->span( {-id=>'navbanner', -class=>'navbanner'},
      "Template repository menu:", join("  ", map { $q->span(
                        $_->{current} ?
                          { -class=>"navbanner_current" } : (),
                        $q->a({-href=>$_->{href}, -target=>$_->{target}},
                           $nbsp->($_->{label})))
                     } @sections
                )
              )
      );

    $res;
}

sub customheader
{
    my $res = '';
    if(open(my $cf, $CUSTOM_HEADER))
    {
        $res = join('', <$cf>);
        close $cf;
    }
    $res;
}
