

import torch
print("is there GPU: {}".format(torch.cuda.is_available()))
print("number of GPUs: {}".format(torch.cuda.device_count()))
print("name of GPU: {}".format(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no-gpu"))

print()

print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("gpu count:", torch.cuda.device_count())
print("gpu name:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no-gpu")


