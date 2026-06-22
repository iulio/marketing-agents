az vm create \
    --resource-group rg-marketing-agents \
    --name marketing-agent-vm \
    --location westus2 \
    --image UbuntuLTS \
    --size Standard_B2ats_v2 \
    --admin-username azureuser \
    --generate-ssh-keys \
    --public-ip-sku Standard