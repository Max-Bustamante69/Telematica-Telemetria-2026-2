#!/usr/bin/env bash
# Crea el grupo de seguridad, el par de llaves y la instancia EC2 con AWS CLI.
# Uso:  AWS_REGION=us-east-1 deploy/aws/create-instance.sh
# Requiere: aws cli v2 autenticado (aws sts get-caller-identity debe responder).
set -euo pipefail
REGION="${AWS_REGION:-us-east-1}"
NAME="${NAME:-telemetria-server}"
KEY="${KEY_NAME:-telemetria-key}"
TYPE="${INSTANCE_TYPE:-t3.micro}"
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "== cuenta"
aws sts get-caller-identity --output table

echo "== AMI Ubuntu 24.04 mas reciente en $REGION"
AMI=$(aws ec2 describe-images --region "$REGION" --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*" "Name=state,Values=available" \
  --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text)
echo "AMI=$AMI"

echo "== par de llaves $KEY"
if ! aws ec2 describe-key-pairs --region "$REGION" --key-names "$KEY" >/dev/null 2>&1; then
  aws ec2 create-key-pair --region "$REGION" --key-name "$KEY" --query KeyMaterial --output text > "$HERE/$KEY.pem"
  chmod 600 "$HERE/$KEY.pem"
  echo "llave privada guardada en deploy/aws/$KEY.pem (esta en .gitignore)"
fi

echo "== grupo de seguridad $NAME-sg"
VPC=$(aws ec2 describe-vpcs --region "$REGION" --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
SG=$(aws ec2 describe-security-groups --region "$REGION" --filters "Name=group-name,Values=$NAME-sg" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || true)
if [ -z "$SG" ] || [ "$SG" = "None" ]; then
  SG=$(aws ec2 create-security-group --region "$REGION" --group-name "$NAME-sg" --description "Telemetria TLP" --vpc-id "$VPC" --query GroupId --output text)
  # reglas de acceso: 22 ssh, 5000 udp telemetria, 5001 tcp operadores, 8080 tcp web
  aws ec2 authorize-security-group-ingress --region "$REGION" --group-id "$SG" --ip-permissions \
    'IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=0.0.0.0/0,Description=ssh}]' \
    'IpProtocol=udp,FromPort=5000,ToPort=5000,IpRanges=[{CidrIp=0.0.0.0/0,Description=telemetria-udp}]' \
    'IpProtocol=tcp,FromPort=5001,ToPort=5001,IpRanges=[{CidrIp=0.0.0.0/0,Description=operadores-tcp}]' \
    'IpProtocol=tcp,FromPort=8080,ToPort=8080,IpRanges=[{CidrIp=0.0.0.0/0,Description=web-http}]'
fi
echo "SG=$SG"

echo "== instancia"
ID=$(aws ec2 run-instances --region "$REGION" --image-id "$AMI" --instance-type "$TYPE" \
  --key-name "$KEY" --security-group-ids "$SG" --user-data "file://$HERE/user-data.sh" \
  --metadata-options "HttpTokens=required,HttpEndpoint=enabled" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME}]" \
  --query 'Instances[0].InstanceId' --output text)
echo "InstanceId=$ID"
aws ec2 wait instance-running --region "$REGION" --instance-ids "$ID"
IP=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo
echo "IP publica: $IP   (apuntar el registro DNS A a esta IP; ver deploy/dns.md)"
echo "ssh -i deploy/aws/$KEY.pem ubuntu@$IP"
echo "El user-data tarda 2 o 3 minutos en instalar Docker y levantar el contenedor."
