#!/usr/bin/perl
package plugin::define_experiment;
use strict; use warnings;
use Cwd;

#Because this script lives in a subdirectory, and I haven't structured my
#code properly.  See below for further IE-specific fix.
our $HTML_BASE ||= '.';
our $PLUGIN_DIR;
BEGIN{  $PLUGIN_DIR = getcwd();
	-f "barcodeUtil.pm" or chdir('..'), $HTML_BASE = '..' };

# CVS $Revision: 1.17 $ committed on $Date: 2006/09/22 13:21:18 $ by $Author: tbooth $

#Testing - capture all warnings.
# use Carp;
# $SIG{__WARN__} = sub { confess(@_) }; 

# Request some barcodes for yourself.
use barcodeUtil('-connect');
use TableIO;
use List::Util qw(sum min max);
use Data::Dumper;
#use Encode;

our %CONFIG = %{bcgetconfig()};
our $PAGE_TITLE = $CONFIG{PAGE_TITLE};
our $PAGE_DESC = $CONFIG{PAGE_DESC};

our $STRICT_USER_NAMES = $barcodeUtil::STRICT_USER_NAMES;
our $STYLESHEET = $barcodeUtil::STYLESHEET;
our $ENABLE_PRINTING = $barcodeUtil::ENABLE_PRINTING;
our $MAX_CODES = $barcodeUtil::MAX_CODES;

#A CGI query object and database handle
our $q = bcgetqueryobj();
our $dbh = bcgetdbobj()->get_handle();

#our $RETURN_URL = $q->escape($q->url(-query=>1));
our $RETURN_URL = $q->escape("javascript: self.close()");
# our $TABLE_EDIT="/nanofate/admin/display.php?database=${CONFIG{DATABASE_NAME}}&server=D&schema=data" .
# 	        "&return_url=$RETURN_URL&return_desc=Back%20to%20Handlebar" .
# 	        "&subject=table&table=";
our $TABLE_EDIT="/nanofate/admin/display.php?database=${CONFIG{DATABASE_NAME}}&server=D&schema=data" .
	        "&return_url=$RETURN_URL&return_desc=Close%20Window" .
	        "&subject=table&table=";
our $EXPT_QUERY="report_barcodes.cgi?queryid=120;rm=results;qp_EXPID=";
our $SAMPLES_UNION = bctypetotable('samples_union');

#Trap if I manage to get stuck in some error loop
#due to my crazy error handling.
our $errorloop = 0;

#Other modules
use Data::Dumper; #For teh debugging and some error reporting
use IO::String;
{ package IO::String; no warnings;
  sub str{${shift()->string_ref }} }

#Get params
our $username = lc($q->param("username") || '');

# More ugly globals
our($exp_id, @tissue, %total_codes, %first_code, %exposure_dose, %sampling_time, %reps, $ion_purity);
our($new_collection_id);

#Set auto-newline so the HTML source is legible
$\ = "\n";

#On FF and Chrome I can just do $HTML_BASE = '..' but my old
#Nemesis IE doesn't like that, oh no, so now that I have the query
#object I can come up with the base URL myself.
($HTML_BASE) = $q->url() =~ ( $HTML_BASE eq '.' ? qr/(.*\/)/ : qr/(.*\/).*\// ) ;

#Things we may need to do:
#
# 1) Display the custom form
# 2) Allocate some barcodes and fill them in
#   a) Validate
#   b) Allocate codes
#   c) Insert data
#   d) Make a collection

#Validate user, numbers, etc.
sub main
{
    my $error = "";

MAIN: for(1){

    eval{ get_batch_list() } or $error =
		"Internal error - cannot read np_batch table.  Is the plugin running on the NanaoFATE database?",
		last MAIN;

    if($q->param("generate")) #2
    {
	$q->delete("generate");	

	#Some quick checking
	$username or $error =
		"You need to supply a user name - click <u>Show Users</u> to see a list.", last MAIN;
	bcchkuser($username) or $error = 
		"The user '$username' is not known - click <u>Show Users</u> to see a list.", last MAIN;
	
	#Validate the rest of the form.
	eval{ validate_mainform() } or $error =
		"Your request could not be processed - $@.", last MAIN;

	#Allocate the codes
	allocate_codes_and_collections();

	#Load all the data
	eval{ load_the_data() };
	if($@){
	    if($@ =~ /^DBD::Pg::st/)
	    {
		(my $errstr = $dbh->errstr()) =~
		    s[^ERROR:\s+null value in column "([^"]+)" violates .*]
		     ["You must set a value for " . ucfirst(bczapunderscores($1))]e;
		
		$error = "Data validation error - $errstr."; 
	    }
	    else { die $@ } # Not an SQL error after all.
	    last MAIN;
	}

	#Done
	bccommit();

	print bcheader(),
	    bcstarthtml("$PAGE_TITLE - Experiment Defined", -xbase=>$HTML_BASE),
	    "<h1>All done - $total_codes{all} codes were allocated:</h1>",
	    "<div style='padding:16px'>",
	    make_download_links(),
	    "</div>";
	
    }

    #otherwise must be a new request or an error so show the form:
    print bcheader();

    my($usage_notes, $unfh);
    if( open $unfh, "<$PLUGIN_DIR/define_experiment_usage_notes.html" )
    {
	$usage_notes = join("\n", <$unfh>);
	close $unfh;
    }

    print bcstarthtml("$PAGE_TITLE - Define an Experiment and Generate Codes", -xbase=>$HTML_BASE),
	  bcnavbanner(),
	  bch1(($PAGE_DESC ? "$PAGE_DESC - " : "") . "Define Experiment"),
	  mainform(), $q->hr,
          $q->a( {-name => 'notes'}, "" ),
	  $q->p( $q->h4("Notes:"), 
	      ($usage_notes || 
	      $q->ul( {-id=>"noteslist"},
		$q->li([ $q->a({-name=>'note1'}, "") . "Usage notes to go in here...",]) 
	      ))
	  );
		    
    
}
#Ending bit
if($error)
{
    print bcheader(), bcstarthtml("Error - $PAGE_TITLE", -xbase=>$HTML_BASE);
    $error =~ s/\n/<br \/>\n/g;
    print $q->p({-class=>"errorbox"},
	        "The following error occured:\n<br /><br />$error");

    #Log the error too
    bclogevent( 'error', $username || 'blank', 0, undef, $error );
		
    #Clear params and go again:
    if($errorloop++)
    {
	die "Oh dear - this script is broken.";
    }
    else
    {
	main();
    }
}
else
{
    print $q->end_div(), bcfooter();
}    
};#done main

sub validate_mainform
{
    #Let's have a look.  We already have a valid user name.

    #exp_id must be valid (ie. valid collection nickname and no spaces) and unique
    $exp_id = $q->param('exp_id');
    for($exp_id)
    {
	s/^\s+//, s/\s+$//, s/(.+)/lc($1)/e;
	/./ or die "You must give an Experiment ID for your experiment.\n";
	/[^\w]/ and die "The Experiment ID may only contain letters, numbers and underscores.\n";
	/[[:lower:]]/ or die "The Experiment ID must contain at least one letter.\n";

	get_experiment_ids()->{$_} and die "The Experiment ID '$_' is already in use.\n";
	bcgetcollectioninfo($_) and die "The Experiment ID '$_' conflicts with an existing collection.\n";
    }

    #tissue - you need to select something
    @tissue = $q->param('tissue');
    @tissue or die "You need to select at least one tissue type for your samples.\n";

    #storage_location
    $q->param('storage_location') or die "You need to say where these samples will be stored.\n";

    #subject
    #ecotox_protocol
    #exposure_medium
    #np_carrier
    #np_batch_id
    #np_pre_protocol
    #...all of these are tainted.  I could re-validate against the lists but since the user can put whatever
    #they like into the spreadsheet I'll just throw it at the database in the normal manner.
    #np_comments

    #np_exposure_dose - split into lines, but otherwise let the database sort it out.
    #np_sampling_time - ditto
    $exposure_dose{np} = split_lines('np_exposure_dose');
    $sampling_time{np} = split_lines('np_sampling_time');

    if   (@{$exposure_dose{np}}){ @{$sampling_time{np}} = ('') unless @{$sampling_time{np}} }
    elsif(@{$sampling_time{np}}){ @{$exposure_dose{np}} = ('') unless @{$exposure_dose{np}} };

    #One sample per tissue, per dose, per sampling time, per replicate.
    $total_codes{np} = @tissue * @{$exposure_dose{np}} * @{$sampling_time{np}};
    if($total_codes{np})
    {
	$q->param('np_batch_id') or
	    die "You have entered doses or timepoints for a nanoparticle exposure; please select the nanoparticle batch.\n";
	$q->param('np_reps') or
	    die "You have specified a nanoparticle exposure; please set the number of replicates.\n";
    }
    $total_codes{np} *= ($reps{np} = int($q->param('np_reps')) );

    #ion_chemical_cas
    #ion_carrier
    #ion_supplier
    #ion_comments
    #...as above, no validation.

    #ion_purity - remove '%' and trim
    if($ion_purity = $q->param('ion_purity'))
    {
	$ion_purity =~ s/\s|%//g;
    }

    #ion_exposure_dose
    #ion_sampling_time
    $exposure_dose{ion} = split_lines('ion_exposure_dose');
    $sampling_time{ion} = split_lines('ion_sampling_time');

    if   (@{$exposure_dose{ion}}){ @{$sampling_time{ion}} = ('') unless  @{$sampling_time{ion}} }
    elsif(@{$sampling_time{ion}}){ @{$exposure_dose{ion}} = ('') unless  @{$exposure_dose{ion}} };

    $total_codes{ion} =  @tissue * @{$exposure_dose{ion}} * @{$sampling_time{ion}};
    if($total_codes{ion})
    {
	$q->param('ion_chemical_cas') or
	    die "You have entered doses or timepoints for an ion exposure; please select the Chemical CAS#.\n";
	$q->param('ion_reps') or
	    die "You have specified an ion exposure; please set the number of replicates.\n";
    }
    $total_codes{ion} *= ($reps{ion} = int($q->param('ion_reps')) );

    #carrier_oxposure_dose
    #carrier_sampling_time
    $exposure_dose{carrier} = split_lines('carrier_exposure_dose');
    $sampling_time{carrier} = split_lines('carrier_sampling_time');

    if   (@{$exposure_dose{carrier}}){ @{$sampling_time{carrier}} = ('') unless @{$sampling_time{carrier}} }
    elsif(@{$sampling_time{carrier}}){ @{$exposure_dose{carrier}} = ('') unless @{$exposure_dose{carrier}} };

    $total_codes{carrier} =  @tissue * @{$exposure_dose{carrier}} * @{$sampling_time{carrier}};
    if($total_codes{carrier} && !$q->param('carrier_reps'))
    {
	die "You have specified an carrier exposure; please set the number of replicates.\n";
    }
    $total_codes{carrier} *= ($reps{carrier} = int($q->param('carrier_reps')) );

    #Sanity check the number of samples 
    if( sum(values(%total_codes)) > $MAX_CODES )
    {
	die "Trying to allocate >$MAX_CODES codes in one go failed.\n";
    }

    #Ensure something is being allocated
    $total_codes{all} = $total_codes{np} + $total_codes{ion} + $total_codes{carrier};
    if($total_codes{all} == 0)
    {
	die "You need to define at least one exposure experiment by filling in exposure doses or sampling times.\n";
    }

    1;
}

sub split_lines
{
    #Need to be sure to trim out carriage returns.
    [ map {s/\s/ /g;$_} grep {/\S+/} split("\n", $q->param($_[0])) ];
}

sub allocate_codes_and_collections
{
    #This bit will make the entries in barcode_allocation and barcode_collection
    #by calling bcallocate, bccreatecollection and bcappendtocollection

    #By default bcallocate commits before logging the allocation, but I don't want to
    #commit to the allocation until I'm done loading the data too!

    #Create the collection first
    $new_collection_id = bccreatecollection(undef, $username, $exp_id, "Samples from exposure $exp_id");

    for my $foo(qw(np ion carrier))
    {
	if($total_codes{$foo})
	{
	    $first_code{$foo} = bcallocate($total_codes{$foo}, $username, "${foo}_exposure_sample",
					"Samples from exposure $exp_id", 1);
	    my $last_code = $first_code{$foo} + $total_codes{$foo} - 1;

	    #add codes to collection
	    bcappendtocollection($new_collection_id, [$first_code{$foo}..$last_code]);
	}
    }

}

sub load_the_data
{
    my $inserth;
    my ($nn, $st);
    my @statics;
    my $foo;

    $foo = 'np';
    if(@{$exposure_dose{$foo}} * @{$sampling_time{$foo}})
    {
	#MP stuff first
	$inserth = bcprepare("
            INSERT INTO " . bctypetotable("${foo}_exposure_sample") . "(
	    creation_date, barcode, created_by, comments, 
	    experiment_id, storage_location, subject, ecotox_protocol, exposure_medium, np_batch_id, np_carrier, 
	    np_pre_treatment, exposure_type, exposure_dose, sampling_time, tissue) VALUES (
	    now()::date, " . join(', ', ('?') x 15)
	    .")");

	#Marshall static values
	@statics = map {$q->param($_) || undef} 
	    qw(storage_location subject ecotox_protocol exposure_medium np_batch_id np_carrier np_pre_protocol);

	$nn = $first_code{$foo};
	$st = what_sort_of_study_is_it($foo);

	#Super loop through tissues * doses * timepoints * reps
	for(cartesian(\@tissue, $exposure_dose{$foo}, $sampling_time{$foo}, [1..$reps{$foo}]))
	{
	    my $comment = "rep $_->[3] of $reps{$foo}";
	    $comment .= (". " . $q->param("${foo}_comments")) if defined($q->param("${foo}_comments"));

	    $inserth->execute($nn++, $username, $comment,
			      $exp_id, @statics, 
			      $st, $_->[1], $_->[2], $_->[0]);
	}
    }

    $foo = 'ion';
    if(@{$exposure_dose{$foo}} * @{$sampling_time{$foo}})
    {
	$inserth = bcprepare("
            INSERT INTO " . bctypetotable("${foo}_exposure_sample") . "(
	    creation_date, barcode, created_by, comments, 
	    experiment_id, storage_location, subject, ecotox_protocol, exposure_medium, chemical_cas, ion_carrier, ion_supplier, 
	    ion_purity, exposure_type, exposure_dose, sampling_time, tissue) VALUES (
	    now()::date, " . join(', ', ('?') x 16)
	    .")");

	#Marshall static values
	@statics = map {$q->param($_) || undef} 
	    qw(storage_location subject ecotox_protocol exposure_medium ion_chemical_cas ion_carrier ion_supplier);

	$nn = $first_code{$foo};
	$st = what_sort_of_study_is_it($foo);

	#Ion purity needs to be set
	$ion_purity or die "Ion purity needs to be specified if you are logging ion exposures\n";

	#Super loop through tissues * doses * timepoints * reps
	for(cartesian(\@tissue, $exposure_dose{$foo}, $sampling_time{$foo}, [1..$reps{$foo}]))
	{
	    my $comment = "rep $_->[3] of $reps{$foo}";
	    $comment .= (". " . $q->param("${foo}_comments")) if defined($q->param("${foo}_comments"));

	    $inserth->execute($nn++, $username, $comment,
			      $exp_id, @statics, $ion_purity,
			      $st, $_->[1], $_->[2], $_->[0]);
	}
    }

    $foo = 'carrier';
    if(@{$exposure_dose{$foo}} * @{$sampling_time{$foo}})
    {
	$inserth = bcprepare("
            INSERT INTO " . bctypetotable("${foo}_exposure_sample") . "(
	    creation_date, barcode, created_by, comments, 
	    experiment_id, storage_location, subject, ecotox_protocol, exposure_medium, np_carrier, 
	    exposure_type, exposure_dose, sampling_time, tissue) VALUES (
	    now()::date, " . join(', ', ('?') x 13)
	    .")");

	#Marshall static values
	@statics = map {$q->param($_) || undef} 
	    qw(storage_location subject ecotox_protocol exposure_medium np_carrier);

	$nn = $first_code{$foo};
	$st = what_sort_of_study_is_it($foo);

	#Super loop through tissues * doses * timepoints * reps
	for(cartesian(\@tissue, $exposure_dose{$foo}, $sampling_time{$foo}, [1..$reps{$foo}]))
	{
	    my $comment = "rep $_->[3] of $reps{$foo}";
	    $comment .= (". " . $q->param("${foo}_comments")) if defined($q->param("${foo}_comments"));

	    $inserth->execute($nn++, $username, $comment,
			      $exp_id, @statics, 
			      $st, $_->[1], $_->[2], $_->[0]);
	}
    }
}

# exposure_type should be "dose course" or "time course" but we also allow "dose+time course"
sub what_sort_of_study_is_it
{
    my( $key ) = @_;
    my( $exp, $time ) = ( scalar(@{$exposure_dose{$key}}) , scalar(@{$sampling_time{$key}}) );

    if($exp == 1 && $time == 1){ return "single sample" }
    if($exp == 1){ return "time course" };
    if($time == 1){ return "dose course" };
    return "dose+time course";
}   

#Return a chunk of HTML with links to the allocated code blocks.
sub make_download_links
{
    my $ios = new IO::String;
    for my $foo(qw(np ion carrier))
    {
	if($total_codes{$foo})
	{
	    my $dl_link = "request_barcodes.cgi?reqexp=1;bcreqrange=$first_code{$foo};username=" . $q->escape($username);
	    my $pr_link = "print_barcodes.cgi?fromcode=" . bcquote($first_code{$foo}) . 
			   ";tocode=" . bcquote($first_code{$foo} + $total_codes{$foo} - 1) . 
			   ";username=" . $q->escape($username);

	    print $ios
		  $q->a({-href=>$dl_link}, "Download"), " / ",
		  $q->a({-href=>$pr_link}, "Print"), " codes for " . uc($foo). " exposure.",
		  "<br /><br />\n";
	}
    }
    print $ios
	  "Summarise experiment ",
	  $q->a({-href=>"$EXPT_QUERY" . $q->escape($exp_id) . "#results"}, "$exp_id in report maker."),
	  "<br /><br />\n";

    print $ios
	  "All samples were also added to collection ", 
	  $q->a({-href=>"collect_barcodes.cgi?rm=edit;c=$new_collection_id"}, 
		bcgetcollectionprefix() . ".$new_collection_id."),
	  $q->br(), $q->hr(), "\n";

    $ios->str;
}

sub get_experiment_ids
{
    #Get a hash of all existing experiment_ids->number_of_samples
    our $_exp_ids ||= $dbh->selectall_hashref("
	SELECT experiment_id, count(*) FROM $SAMPLES_UNION
	GROUP BY experiment_id;
    ", 1);
}

# TODO - make a function row(...) that wraps all the Tr, td stuff so I can just say:
# row ( 'Label', '<input>', { -foo => bar }, 'comment')

sub popup
{
    #Helper used in the next function for popup links
    my $page = $_[0]; #? What escaping is appropriate ?
    my $title = $_[1] || 'Handlebar';
    { href =>  "javascript:;",
      -onClick => "window.open('$page', '$title',
		   'width=800,height=600,resizable=yes,scrollbars=yes');"
    };
}

sub mainform
{
my $ios = new IO::String;

    my $subject_list = get_subject_list();
    my $pre_protocol_list = get_pre_protocol_list();
    my $exp_protocol_list = get_exp_protocol_list();
    my $exp_medium_list = get_exp_medium_list();
    my $batch_list = get_batch_list();
    my $cas_list = get_cas_list();
    my $carrier_list = get_carrier_list();
    my $tissue_list = get_tissue_list();
    my $ion_supplier_list = get_ion_supplier_list();
    my $ion_grade_list = get_ion_grade_list();

    #Generate link to view users or describe a type
    my $userlink = $q->a(popup('request_barcodes.cgi?userpopup=1', 'Info'), "Show users" );
    my $newuserlink = $q->a(popup("new_user_request.cgi?c=1"), "Register new user");

    print $ios
      $q->a({-name=>'generate'}, ''),
      $q->start_form(-name=>"generate", -method=>"POST"),
      $q->h2("Enter a new experiment and create sample barcodes"),
      $q->p("This form will help you to record details of a nanoparticle exposure experiment and will create the appropriate
	     barcodes for you."),
      $q->table( {-class => "formtable"},
	  $q->Tr($q->td( ["User name ", $q->textfield("username"), $userlink, $newuserlink] )),
	  $q->Tr($q->td( ["Experiment ID ", $q->textfield("exp_id") ] ), 
	         $q->td( { -colspan=>2 }, ['Defaults to <i>organism_number</i>, eg daphnia_03'] )),
	  $q->Tr($q->td( ["Subject organism ",
			  $q->popup_menu( -name=>"subject",
					  -values=>[0, map{$_->[0]} @{$subject_list}],
					  -labels=>{0=>"Select...", map{@{$_}[0,1]} @{$subject_list}},
				          -onChange=>'set_exp_id()' ),
			  $q->span(),
			  $q->a(popup("${TABLE_EDIT}organism"), "Edit organism list"),
			 ] )),
	  $q->Tr($q->td( ["Tissues sampled "] ),
	         $q->td( { -colspan=>2 }, [
			  $q->div( { -style=>"display:inline;padding:6px"}, 
				    [ $q->checkbox_group( -name=>"tissue",
					  -values=>[map{$_->[0]} @{$tissue_list}],
					  -labels=>{map{@{$_}[0,1]} @{$tissue_list}},
				        ) ]) ]),
		 $q->td( [$q->a(popup("${TABLE_EDIT}tissue"), "Edit tissues list") ]),
					
		),
	  $q->Tr($q->td( ["Storage location ", $q->textfield(-name => "storage_location",
							     -default => "UNKNOWN" ) ] ),
	         $q->td( { -colspan=>2 }, ['enter where the samples will be stored'] )),
	  $q->Tr($q->td( ["Exposure protocol ",
			  $q->popup_menu( -name=>"ecotox_protocol",
					  -values=>[0, map{$_->[0]} @{$exp_protocol_list}],
					  -labels=>{0=>"Select..."} 
				        ),
			  $q->span(),
			  $q->a(popup("${TABLE_EDIT}ecotox_protocol"), "Edit protocols list"),
				      
			 ] )),
	  $q->Tr($q->td( ["Exposure medium ",
			  $q->popup_menu( -name=>"exposure_medium",
					  -values=>[0, map{$_->[0]} @{$exp_medium_list}],
					  -labels=>{0=>"Select...", map{@{$_}[0,1]} @{$exp_medium_list}},
					 ),
			  $q->span(),
			  $q->a(popup("${TABLE_EDIT}medium"), "Edit media list"),

			  ] )),
	  $q->Tr($q->td( ["Nanoparticle carrier ",
			  $q->popup_menu( -name=>"np_carrier",
					  -values=>[0, map{$_->[0]} @{$carrier_list}],
					  -labels=>{0=>"Select...", map{@{$_}[0,1]} @{$carrier_list}},
					 ),
			  $q->span(),
			  $q->a(popup("${TABLE_EDIT}carrier"), "Edit carriers list"),

			  ] )),

	  #Most times there will be a nanoparticle exposure, but not always
	  $q->Tr($q->td( [ $q->h4("Nanoparticle Exposure") ] )),
	  $q->Tr($q->td( ["Nanoparticle batch "] ),
	         $q->td( { -colspan=>2 }, [
			  $q->popup_menu( -name=>"np_batch_id",
					  -values=>[ 0, map{$_->[0]} @{$batch_list} ],
				          -labels=>{0=>"No exposure", map{@{$_}[0,1]} @{$batch_list} } , 
					) .
	# < < < < < < < < < < < < < < < < +
	$q->a(popup("report_barcodes.cgi?queryid=76;rm=results;qp_BATCH=' +
  		  generate.np_batch_id[generate.np_batch_id.selectedIndex].value
		+ '#results"
	      ), " - See QA")
	# > > > > > > > > > > > > > > > > +
				    ]),
		 $q->td( [$q->a(popup("${TABLE_EDIT}np_batch"), "Browse/edit batch table")] )
		),
	  $q->Tr($q->td( ["Pre-treatment ",
			  $q->popup_menu( -name=>"np_pre_protocol",
					  -values=>[0, map{$_->[0]} @{$pre_protocol_list}],
					  -labels=>{0=>"Select..."} ), '',
			  $q->a(popup("${TABLE_EDIT}pretreatment_protocol"), "Edit pre-treatments list")	      
			 ] )),
	  $q->Tr($q->td( ["Exposure doses ",
			  $q->textarea(-name=>'np_exposure_dose', -rows=>5, -columns=>20), "enter one per line" ] )),
	  $q->Tr($q->td( ["Sampling timepoints ",
			  $q->textarea(-name=>'np_sampling_time', -rows=>5, -columns=>20), "enter one per line" ] )),

	  $q->Tr($q->td( ["Replicates ", $q->textfield('np_reps') ] )),

	  $q->Tr($q->td( ["Comments "] ),
	         $q->td( { -colspan=>2 }, [
			  $q->textarea(-name=>'np_comments', -rows=>3, -columns=>60)
			]),
		 $q->td( [ '' ] )
		),

	  #Ofter there will be an ion exposure
	  $q->Tr($q->td( [ $q->h4("Ion Exposure Control") ] )),
	  $q->Tr($q->td( ["Chemical CAS# ",
			  $q->popup_menu( -name=>"ion_chemical_cas",
					  -values=>[ 0, map{$_->[0]}@{$cas_list}],
				          -labels=>{0=>"No exposure", map{@{$_}[0,1]} @{$cas_list} } ), 
			  $q->span(),
			  $q->a(popup("${TABLE_EDIT}chemical"), "Edit chemicals list"),
				      
			 ] )),
	  $q->Tr($q->td( ["Ion carrier ",
			  $q->popup_menu( -name=>"ion_carrier",
					  -values=>[0, (map{$_->[0]} @{$carrier_list}), 'other'],
					  -labels=>{0=>"Select...", map{@{$_}[0,1]} @{$carrier_list} } ),
			  $q->span(),
	     	          $q->a(popup("${TABLE_EDIT}carrier"), "Edit carriers list"),

			  ] )),
	  $q->Tr($q->td( ["Ion supplier ",

			  $q->popup_menu( -name=>"ion_supplier",
					  -values=>[0, (map{$_->[0]} @{$ion_supplier_list}), 'other'],
					  -labels=>{0=>"Select...", map{@{$_}[0,1]} @{$ion_supplier_list} } ),
			  "if selecting <i>other</i>, please amend it later in the spreadsheet",
			  $q->a(popup("${TABLE_EDIT}ion_supplier"), "Edit suppliers list"),
			  
			  ] )),
	  $q->Tr($q->td( ["Ion purity ",
 			  $q->textfield({-size=>5, -name=>"ion_purity"}),

# 			  $q->popup_menu( -name=>"ion_grade",
# 					  -values=>[0, (map{$_->[0]} @{$ion_grade_list}), 'other'],
# 					  -labels=>{0=>"Select...", map{@{$_}[0,1]} @{$ion_grade_list} } ),
# 			  "if selecting <i>other</i>, please amend it later in the spreadsheet",
# 	     	          $q->a(popup("${TABLE_EDIT}ion_grade"), "Edit grades list"),
			  'as a percentage',
		      
			  ] )),
	  $q->Tr($q->td( ["Exposure doses ",
			  $q->textarea({-name=>"ion_exposure_dose",  -rows=>5, -columns=>20}), "enter one per line" ] )),
	  $q->Tr($q->td( ["Sampling timepoints ",
			  $q->textarea({-name=>"ion_sampling_time", -rows=>5, -columns=>20}), "enter one per line" ] )),
	  $q->Tr($q->td( ["Replicates ", $q->textfield('ion_reps') ] )),

	  $q->Tr($q->td( ["Comments "] ),
	         $q->td( { -colspan=>2 }, [
			  $q->textarea(-name=>'ion_comments', -rows=>3, -columns=>60)
			]),
		 $q->td( [ '' ] )
		),

	  #There may be an exposure to the carrier as control
	  $q->Tr($q->td( [ $q->h4("Carrier Exposure Control") ] )),
	  $q->Tr($q->td( ["Exposure doses ",
			  $q->textarea({-name=>"carrier_exposure_dose",  -rows=>5, -columns=>20}), "enter one per line" ] )),
	  $q->Tr($q->td( ["Sampling timepoints ",
			  $q->textarea({-name=>"carrier_sampling_time", -rows=>5, -columns=>20}), "enter one per line" ] )),
	  $q->Tr($q->td( ["Replicates ", $q->textfield('carrier_reps') ] )),
	  $q->Tr($q->td( ["Comments "] ),
	         $q->td( { -colspan=>2 }, [
			  $q->textarea(-name=>'carrier_comments', -rows=>3, -columns=>60)
			]),
		 $q->td( [ '' ] )
		),

	  $q->Tr($q->td( ["", "", $q->submit( -name=>"generate", -value=>"Submit")] )), 
      ),
      $q->end_form;

#Now we need a JS function which replaces spaces with underscores
    print $ios '<script type="text/javascript">',
	       bczapspaces_js(),
	       '</script>';

#And one to generate a new experiment_id
    print $ios '<script type="text/javascript">
		 function set_exp_id() {

		    var nextids = new Object;
		    var theform = document.generate;
		    
		    if(theform.subject.value == "0") return;
		    ',

		    ( map { "
		      nextids['$_->[0]'] = '" . sprintf("%02d", $_->[2] + 1) . "';"
		      } @{$subject_list} ),

		'   theform.exp_id.value = theform.subject.value + "_" + nextids[theform.subject.value];
		 }
	        </script>';

$ios->str;
}

sub get_subject_list {
    #Returns a list of triples [short_name, display_name, max_id]
    our $_subject_list ||=
     $dbh->selectall_arrayref("
	 SELECT short_name, 
	        display_name, 
		coalesce( max( substring(u.experiment_id FROM '.*_([0-9]*)' )::int) ) AS max_id
         FROM (data.organism o LEFT OUTER JOIN $SAMPLES_UNION u ON o.short_name = substring(u.experiment_id FROM '(.*)_') )  
         GROUP BY short_name, display_name
         ORDER BY display_name");

#    $dbh->selectall_arrayref("SELECT short_name, display_name, floor(random()*20) as count
#	       FROM data.organism ORDER BY display_name");

}

sub get_pre_protocol_list {
    #Either grab from database or just hard-code

    our $_pprotocol_list ||=
      $dbh->selectall_arrayref("SELECT protocol_id FROM data.pretreatment_protocol
		 ORDER BY protocol_id");

	     #("proto-1", "proto-2", "proto-2a", "proto-2b");
}

sub get_exp_protocol_list {
    #Either grab from database or just hard-code

    our $_eprotocol_list ||=
      $dbh->selectall_arrayref("SELECT protocol_id FROM data.ecotox_protocol
		 ORDER BY protocol_id");

	     #("proto-1", "proto-2", "proto-2a", "proto-2b");
}

sub get_batch_list {
    # This will definitely come from the NP_Batch table
    our $_batch_list ||= 
	$dbh->selectall_arrayref("SELECT batch_code, batch_code || ' : ' || manufacturer_info as label
		FROM data.np_batch ORDER BY batch_code");
#     our $_batch_list ||= [
#     map { [$_] }
#     qw( ZN1 ZN2 ZN3 AG1 AG2 AG3 CE1 AG4 AG5 ZN4 ZN5 ZN6 ZN7 AG6 AG7 AG4/2 ZN8 ZN9 ZN10 ZN11 ZN12 ZN13 ZN14 ZN15
#         ZN16 CE2 CE3 Ag6/2 AG6/3 AG7/2 ZN17 ZN18 ZN19 ZN20 AG8 AG9 ZN21 ZN22 ZN23 ZN24 ZN25 ZN26 ZN27 ZN28 ZN29 
# 	ZN30 AG4_No1 CE5 CE6 CE7 AG10 ZN31 ZN32 )
#     ];
}

sub get_cas_list {
    # I need some example CAS numbers...
    our $_cas_list ||=
      $dbh->selectall_arrayref("SELECT cas_no, display_name || ' (' || cas_no || ')' AS display_name
	         FROM data.chemical
		 ORDER BY display_name");

	#    ( '1314-13-2 (zinc oxide)', );
}

sub get_carrier_list {
    our $_carrier_list ||=
      $dbh->selectall_arrayref("SELECT short_name, display_name
	         FROM data.carrier
		 ORDER BY display_name");
}

sub get_exp_medium_list {
    our $_media_list ||= 
      $dbh->selectall_arrayref("SELECT short_name, display_name
	         FROM data.medium
		 ORDER BY display_name");
}

sub get_tissue_list {
    our $_tissue_list ||=
      $dbh->selectall_arrayref("SELECT short_name, display_name
	         FROM data.tissue
		 ORDER BY display_name");
}

sub get_ion_grade_list {
    our $_ion_grade_list ||=
      $dbh->selectall_arrayref("SELECT short_name, display_name
	         FROM data.ion_grade
		 ORDER BY display_name");
}

sub get_ion_supplier_list {
    our $_ion_supplier_list ||=
      $dbh->selectall_arrayref("SELECT short_name, display_name
	         FROM data.ion_supplier
		 ORDER BY display_name");
}

sub formatcodes
{
    #Format a big list of codes using <pre>
    my @codes = map {bcquote $_} @{shift()};
    
    my $ret = "<pre>\n";
    while(my $block = join(', ', splice(@codes, 0, 20)))
    {
	$ret .= "$block\n";
    }
    $ret .= "</pre>";
}

#Standard cartesian product utility function.  I don't want to add an
#extra dependency for this.
sub cartesian {
    my @res = map { [ $_ ] } @{ shift @_ };

    foreach my $inlist (@_) {
        @res = map { my $outlist = $_; map { [ @$outlist, $_ ] } @$inlist } @res;
    }

    return @res;
}

#The hook into main.
{
    main();
    bcdisconnect();
}

