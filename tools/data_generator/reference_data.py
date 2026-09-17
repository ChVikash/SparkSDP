"""Static reference pools used to generate MediCore source data.

All values here are fictional. Facility names and locations come from
README.md section 2; everything else is invented to be plausible for a
North-India healthcare network.
"""

FACILITIES = [
    {
        "facility_id": "F001",
        "facility_name": "City Care Hospital",
        "facility_type": "HOSPITAL",
        "address_line1": "14 Ring Road",
        "city": "Delhi",
        "state": "Delhi",
        "postal_code": "110024",
        "phone": "01143201100",
        "opened_date": "2009-04-15",
        "patient_share": 0.34,
    },
    {
        "facility_id": "F002",
        "facility_name": "Metro Health Hospital",
        "facility_type": "HOSPITAL",
        "address_line1": "Plot 22, Sector 62",
        "city": "Noida",
        "state": "Uttar Pradesh",
        "postal_code": "201309",
        "phone": "01204455200",
        "opened_date": "2013-08-02",
        "patient_share": 0.30,
    },
    {
        "facility_id": "F003",
        "facility_name": "MediCore Diagnostics",
        "facility_type": "DIAGNOSTIC",
        "address_line1": "8 Rajnagar Extension",
        "city": "Ghaziabad",
        "state": "Uttar Pradesh",
        "postal_code": "201017",
        "phone": "01202877300",
        "opened_date": "2017-01-20",
        "patient_share": 0.20,
    },
    {
        "facility_id": "F004",
        "facility_name": "MediCore Specialty Clinic",
        "facility_type": "CLINIC",
        "address_line1": "Tower B, Golf Course Road",
        "city": "Gurgaon",
        "state": "Haryana",
        "postal_code": "122002",
        "phone": "01244566400",
        "opened_date": "2019-11-11",
        "patient_share": 0.16,
    },
]

# Encounter types a facility is capable of producing. A diagnostic centre
# does not admit inpatients; a clinic does not run an emergency department.
FACILITY_ENCOUNTER_TYPES = {
    "HOSPITAL": [
        ("OUTPATIENT", 0.55),
        ("INPATIENT", 0.18),
        ("EMERGENCY", 0.17),
        ("DIAGNOSTIC", 0.10),
    ],
    "DIAGNOSTIC": [("DIAGNOSTIC", 0.85), ("OUTPATIENT", 0.15)],
    "CLINIC": [("OUTPATIENT", 0.90), ("DIAGNOSTIC", 0.10)],
}

FIRST_NAMES_MALE = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Krishna",
    "Ishaan", "Rohan", "Rahul", "Karan", "Nikhil", "Siddharth", "Ankit",
    "Manish", "Rajesh", "Sanjay", "Vikram", "Deepak", "Amit", "Suresh",
    "Harsh", "Gaurav", "Pranav", "Kabir", "Yash", "Dhruv", "Naveen", "Tarun",
]

FIRST_NAMES_FEMALE = [
    "Aadhya", "Ananya", "Diya", "Ishita", "Kavya", "Myra", "Saanvi", "Aanya",
    "Priya", "Neha", "Pooja", "Sneha", "Anjali", "Divya", "Shruti", "Meera",
    "Ritu", "Swati", "Nisha", "Kiran", "Rekha", "Sunita", "Geeta", "Lakshmi",
    "Tanvi", "Riya", "Shalini", "Namrata", "Aarti", "Preeti",
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Agarwal", "Chauhan",
    "Yadav", "Mishra", "Jain", "Bansal", "Malhotra", "Kapoor", "Chopra",
    "Mehta", "Bhatia", "Saxena", "Tiwari", "Pandey", "Joshi", "Nair",
    "Reddy", "Rao", "Iyer", "Menon", "Das", "Bose", "Ghosh", "Dutta", "Sinha",
]

GENDERS = [("M", 0.49), ("F", 0.50), ("O", 0.01)]

# Weighted so staffing reflects demand: a network staffs far more general
# physicians and emergency cover than it does dermatologists. Uniform
# assignment leaves high-demand specialties accidentally unstaffed.
SPECIALTIES = [
    ("General Medicine", 0.20),
    ("Emergency Medicine", 0.10),
    ("Radiology", 0.10),
    ("Pediatrics", 0.09),
    ("Orthopedics", 0.08),
    ("Cardiology", 0.07),
    ("Obstetrics & Gynaecology", 0.07),
    ("Pathology", 0.07),
    ("Endocrinology", 0.05),
    ("Pulmonology", 0.05),
    ("Gastroenterology", 0.05),
    ("Nephrology", 0.03),
    ("Dermatology", 0.02),
    ("Neurology", 0.02),
]

CREDENTIALS = ["MBBS", "MD", "MS", "DM", "MCh", "DNB"]

# ICD-10-style codes. Kept to common presentations so encounter volumes
# look like a real outpatient-heavy network. The specialty is the one that
# would usually manage the condition, so provider workload and specialty
# demand stay coherent rather than randomly assigned.
# (code, description, weight, managing_specialty, female_only)
DIAGNOSES = [
    ("E11.9", "Type 2 diabetes mellitus without complications", 0.11, "Endocrinology", False),
    ("I10", "Essential (primary) hypertension", 0.12, "General Medicine", False),
    ("J06.9", "Acute upper respiratory infection, unspecified", 0.10, "General Medicine", False),
    ("K21.0", "Gastro-oesophageal reflux disease with oesophagitis", 0.06, "Gastroenterology", False),
    ("M54.5", "Low back pain", 0.08, "Orthopedics", False),
    ("E78.5", "Hyperlipidaemia, unspecified", 0.07, "General Medicine", False),
    ("J45.909", "Unspecified asthma, uncomplicated", 0.05, "Pulmonology", False),
    ("N39.0", "Urinary tract infection, site not specified", 0.05, "General Medicine", False),
    ("R51", "Headache", 0.05, "Neurology", False),
    ("E03.9", "Hypothyroidism, unspecified", 0.06, "Endocrinology", False),
    ("A09", "Infectious gastroenteritis and colitis, unspecified", 0.05, "General Medicine", False),
    ("S52.501", "Fracture of lower end of right radius", 0.03, "Orthopedics", False),
    ("I25.10", "Atherosclerotic heart disease of native coronary artery", 0.04, "Cardiology", False),
    ("N18.3", "Chronic kidney disease, stage 3", 0.03, "Nephrology", False),
    ("O26.899", "Pregnancy-related condition, unspecified", 0.04, "Obstetrics & Gynaecology", True),
    ("L20.9", "Atopic dermatitis, unspecified", 0.03, "Dermatology", False),
    ("R10.9", "Unspecified abdominal pain", 0.03, "General Medicine", False),
]

# (test_code, test_name, unit, ref_low, ref_high, decimals)
LAB_TESTS = [
    ("HB", "Haemoglobin", "g/dL", 12.0, 16.5, 1),
    ("WBC", "White Blood Cell Count", "10^3/uL", 4.0, 11.0, 1),
    ("PLT", "Platelet Count", "10^3/uL", 150.0, 410.0, 0),
    ("GLUF", "Fasting Blood Glucose", "mg/dL", 70.0, 100.0, 0),
    ("HBA1C", "Glycated Haemoglobin", "%", 4.0, 5.7, 1),
    ("CREA", "Serum Creatinine", "mg/dL", 0.6, 1.3, 2),
    ("CHOL", "Total Cholesterol", "mg/dL", 125.0, 200.0, 0),
    ("LDL", "LDL Cholesterol", "mg/dL", 50.0, 100.0, 0),
    ("TSH", "Thyroid Stimulating Hormone", "uIU/mL", 0.4, 4.0, 2),
    ("ALT", "Alanine Aminotransferase", "U/L", 7.0, 56.0, 0),
    ("VITD", "Vitamin D (25-OH)", "ng/mL", 30.0, 100.0, 1),
    ("NA", "Serum Sodium", "mmol/L", 135.0, 145.0, 0),
    ("K", "Serum Potassium", "mmol/L", 3.5, 5.1, 1),
    ("CRP", "C-Reactive Protein", "mg/L", 0.0, 5.0, 1),
]

# (medication_code, medication_name, dosage, frequency)
MEDICATIONS = [
    ("MED001", "Metformin", "500 mg", "BD"),
    ("MED002", "Amlodipine", "5 mg", "OD"),
    ("MED003", "Atorvastatin", "10 mg", "OD"),
    ("MED004", "Amoxicillin", "500 mg", "TDS"),
    ("MED005", "Pantoprazole", "40 mg", "OD"),
    ("MED006", "Levothyroxine", "50 mcg", "OD"),
    ("MED007", "Salbutamol Inhaler", "100 mcg", "PRN"),
    ("MED008", "Paracetamol", "650 mg", "TDS"),
    ("MED009", "Insulin Glargine", "10 IU", "OD"),
    ("MED010", "Losartan", "50 mg", "OD"),
    ("MED011", "Cetirizine", "10 mg", "OD"),
    ("MED012", "Azithromycin", "500 mg", "OD"),
]

INSURERS = [
    ("Sanjeevani Health Insurance", 0.22),
    ("Bharat Care Assurance", 0.18),
    ("MetroSecure Health", 0.15),
    ("Arogya Shield", 0.14),
    ("NorthStar Health Cover", 0.11),
    ("State Health Scheme", 0.12),
    ("Self Pay", 0.08),
]

# Claim service categories. One encounter can bill several of these, which
# is what makes the encounter -> claims relationship 1:N.
CLAIM_SERVICE_CATEGORIES = [
    ("FACILITY_FEE", 0.34),
    ("PROFESSIONAL_FEE", 0.31),
    ("LAB", 0.20),
    ("PHARMACY", 0.15),
]

CLAIM_STATUSES = [
    ("PAID", 0.52),
    ("APPROVED", 0.16),
    ("DENIED", 0.13),
    ("IN_REVIEW", 0.12),
    ("SUBMITTED", 0.07),
]

DENIAL_REASONS = [
    "Service not covered under policy",
    "Pre-authorisation not obtained",
    "Policy lapsed on date of service",
    "Duplicate claim submission",
    "Incomplete clinical documentation",
    "Treatment outside network",
    "Exceeds annual benefit limit",
    "Waiting period not completed",
]

EMAIL_DOMAINS = ["gmail.com", "yahoo.co.in", "outlook.com", "rediffmail.com"]
