$ErrorActionPreference = "Stop"

python cli.py --input sample_data/snowball_inquiry_zh.txt --output outputs/sample_snowball
python cli.py --input sample_data/fcn_quote_zh.txt --output outputs/sample_fcn
python cli.py --input sample_data/european_option_email_en.txt --output outputs/sample_option
python cli.py --input sample_data/reference_case_09_limited_loss_snowball.txt --output outputs/reference_case_09
python cli.py --input sample_data/reference_case_11_dcn_unsupported.txt --output outputs/reference_case_11
python cli.py --input sample_data/reference_case_12_sharkfin_unsupported.txt --output outputs/reference_case_12
python cli.py --input sample_data/reference_case_13_snowball_two_choices.txt --output outputs/reference_case_13
