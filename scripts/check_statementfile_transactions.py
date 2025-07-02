from profiles.models import UploadedFile, Transaction

files = [
    "062524 WellsFargo.pdf",
    "112524 WellsFargo.pdf",
    "022324 WellsFargo.pdf",
    "WF_Checking_2059.csv",
    "2024_Capital_one_transaction_download.csv",
    "20240210-statements-7429-.pdf",
    "20240612-statements-7429-.pdf",
]

for fname in files:
    sf = UploadedFile.objects.filter(original_filename=fname).first()
    if sf:
        count = Transaction.objects.filter(statement_file=sf).count()
        print(f"{fname}: {count} transactions")
    else:
        print(f"{fname}: NO FILE")
