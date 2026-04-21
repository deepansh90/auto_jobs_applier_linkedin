###################################################### CONFIGURE YOUR TOOLS HERE ######################################################
  
# >>>>>>>>>>> Job Search Filters <<<<<<<<<<<

# These Sentences are Searched in LinkedIn
# Enter your search terms inside '[ ]' with quotes ' "searching title" ' for each search followed by comma ', ' Eg: ["Software Engineer", "Software Developer", "Selenium Developer"]
search_terms = ["Lead Engineer", "Staff Engineer", "Principal Engineer", "Engineering Manager"]

# Search location, this will be filled in "City, state, or zip code" search box. If left empty as "", tool will not fill it.
search_location = "Noida, Uttar Pradesh, India"               # Some valid examples: "", "United States", "India", "Chicago, Illinois, United States", "90001, Los Angeles, California, United States", "Bengaluru, Karnataka, India", etc.


''' 
You could set your preferences or leave them as empty to not select options except for 'True or False' options. Below are some valid examples for leaving them empty:

question_1 = ""                    # answer1, answer2, answer3, etc.
question_2 = []                    # (multiple select)
question_3 = []                    # (dynamic multiple select)

'''

sort_by = "Most recent"            # "Most recent", "Most relevant" or ("" to not select) 
date_posted = "Past month"         # "Any time", "Past month", "Past week", "Past 24 hours" or ("" to not select)
salary = ""                        # "$40,000+", "$60,000+", "$80,000+", "$100,000+", "$120,000+", "$140,000+", "$160,000+", "$180,000+", "$200,000+"

# True = only Easy Apply jobs (adds f_EA=true to the job search URL and toggles Easy Apply in All filters). False = include non–Easy Apply listings too.
easy_apply_only = True             # True or False, Note: True or False are case-sensitive

experience_level = ["Mid-Senior level", "Director"]    # (multiple select) "Internship", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive"
job_type = ["Full-time"]                      # (multiple select) "Full-time", "Part-time", "Contract", "Temporary", "Volunteer", "Internship", "Other"
on_site = ["On-site", "Remote", "Hybrid"]                       # (multiple select) "On-site", "Remote", "Hybrid"

companies = []                     # (dynamic multiple select) make sure the name you type in list exactly matches with the company name you're looking for, including capitals. 
                                   # Eg: "7-eleven", "Google","X, the moonshot factory","YouTube","CapitalG","Adometry (acquired by Google)","Meta","Apple","Byte Dance","Netflix", "Snowflake","Mineral.ai","Microsoft","JP Morgan","Barclays","Visa","American Express", "Snap Inc", "JPMorgan Chase & Co.", "Tata Consultancy Services", "Recruiting from Scratch", "Epic", and so on...
location = []                      # (dynamic multiple select)
industry = []                      # (dynamic multiple select)
job_function = []                  # (dynamic multiple select)
job_titles = []                    # (dynamic multiple select)
benefits = []                      # (dynamic multiple select)
commitments = []                   # (dynamic multiple select)

under_10_applicants = False        # True or False, Note: True or False are case-sensitive
in_your_network = False            # True or False, Note: True or False are case-sensitive
fair_chance_employer = False       # True or False, Note: True or False are case-sensitive



# >>>>>>>>>>> LinkedIn Settings <<<<<<<<<<<

# Do you want to randomize the search order for search_terms?
randomize_search_order = False     # True of False



## Skip irrelevant jobs
# Avoid applying to these companies, and companies with these bad words in their 'About Company' section...
about_company_bad_words = ["Crossover", "Staffing", "Recruiting", "Jobot"]       # (dynamic multiple search) or leave empty as []. Ex: ["Staffing", "Recruiting", "Name of Company you don't want to apply to"]

# Skip checking for `about_company_bad_words` for these companies if they have these good words in their 'About Company' section... [Exceptions, For example, I want to apply to "Robert Half" although it's a staffing company]
about_company_good_words = []      # (dynamic multiple search) or leave empty as []. Ex: ["Robert Half", "Dice"]


# Avoid applying to these companies if they have these bad words in their 'Job Description' section...  (In development)
bad_words = ["US Citizen","USA Citizen","No C2C", "No Corp2Corp", ".NET", "Embedded Programming", "PHP", "Ruby"]                     # (dynamic multiple search) or leave empty as []. Case Insensitive. Ex: ["word_1", "phrase 1", "word word", "polygraph", "US Citizenship", "Security Clearance"]

# Do you have an active Security Clearance? (True for Yes and False for No)
security_clearance = False         # True or False, Note: True or False are case-sensitive

# Do you have a Masters degree? (True for Yes and False for No). If True, the tool will apply to jobs containing the word 'master' in their job description and if it's experience required <= current_experience + 2 and current_experience is not set as -1. 
did_masters = True                 # True or False, Note: True or False are case-sensitive

# Avoid applying to jobs if their required experience is above your current_experience. (Set value as -1 if you want to apply to all ignoring their required experience...)
current_experience = 15             # Minimum experience (E.g. 5, 10, 15...)
min_experience = 5                 # Minimum years of experience required by the job (skip if less)
##


# Keep the External Application tabs open? (Note: RECOMMENDED TO LEAVE IT AS TRUE, if you set it false, be sure to CLOSE ALL TABS BEFORE CLOSING THE BROWSER!!!)
close_tabs = True                  # True or False, Note: True or False are case-sensitive

# After how many number of applications in current search should the bot switch to next search? 
switch_number = 30                 # Only numbers greater than 0... Don't put in quotes

## Upcoming features (In Development)
# Send connection requests to HR's
connect_hr = False                  # True or False, Note: True or False are case-sensitive

# What message do you want to send during connection request? (Max. 200 Characters)
connect_request_message = ""       # Leave Empty to send connection request without personalized invitation (recommended to leave it empty, since you only get 10 per month without LinkedIn Premium*)

# Do you want the program to run continuously until you stop it? (Beta)
run_non_stop = False               # True or False, Note: True or False are case-sensitive
'''
Note: Will be treated as False if `run_in_background = True`
'''
alternate_sortby = True            # True or False, Note: True or False are case-sensitive
cycle_date_posted = True           # True or False, Note: True or False are case-sensitive
stop_date_cycle_at_24hr = True     # True or False, Note: True or False are case-sensitive
##




############################################################################################################