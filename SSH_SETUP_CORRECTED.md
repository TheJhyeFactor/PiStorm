# SSH Key Setup - Corrected Instructions

## On Your Pi (jhye@pi-lab-1)

Since you generated a new SSH key on the Pi, let's set up bidirectional authentication properly.

### 1. Create SSH directory and set permissions
```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
```

### 2. Add Windows PC's public key to Pi (for PC→Pi access)
```bash
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOE5MQ7edWA7D5Ai2L9EfngN/7dR2P2rLzDzEm0XAage Jhye@DESKTOP-P2GHC2L" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 3. Copy Pi's public key for PC→Pi authentication
```bash
cat ~/.ssh/wifi_crack_key.pub
```

### 4. Test SSH from Pi to PC (if needed for file transfers)
```bash
ssh-copy-id -i ~/.ssh/wifi_crack_key.pub Jhye@DESKTOP-P2GHC2L
```

## On Your Windows PC

### 1. Test SSH connection to Pi
```bash
ssh -i ~/.ssh/wifi_crack_key jhye@192.168.0.218
```

### 2. If you need Pi→PC access, add Pi's public key
Copy the output from `cat ~/.ssh/wifi_crack_key.pub` on the Pi and add it to your Windows SSH config.

## Verification Commands

### Test from Windows PC:
```bash
ssh jhye@192.168.0.218 "echo 'SSH connection successful'"
```

### Test API connectivity:
```bash
curl -H "Authorization: Bearer 4c273a289160db43476e823cfedc262578a7b96407c4728f4ecb24aad86c776f" http://192.168.0.218:5000/api/status
```

## Updated Configuration

The Windows crack_listener.py script now includes:
- ✅ API Key: `4c273a289160db43476e823cfedc262578a7b96407c4728f4ecb24aad86c776f`
- ✅ Authentication headers in API calls
- ✅ Proper error handling for unauthorized responses

## File Transfer Method

For automatic file transfers, your Pi can use:

```bash
# Copy .cap file to Windows PC
scp capture.cap jhye@DESKTOP-P2GHC2L:C:/Users/Jhye/wifi-crack-pc/incoming/

# Or using rsync
rsync -avz capture.cap jhye@DESKTOP-P2GHC2L:C:/Users/Jhye/wifi-crack-pc/incoming/
```

The Windows listener will automatically detect and process any files placed in the incoming directory.