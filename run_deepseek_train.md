Absolument ! Voici un script ZSH complet pour automatiser l'entraînement de votre modèle DeepSeek sur macOS avec GPU M2/M3. Ce script gère l'installation des dépendances, la préparation des données et le lancement de l'entraînement.

```zsh:run_deepseek_train.zsh
#!/bin/zsh

# ----------------------------------------------------------------------
# DeepSeek Fine-Tuning Script for Apple Silicon (M1/M2/M3)
# Optimisé pour GPU MPS - macOS Sonoma+
# ----------------------------------------------------------------------

# ======= CONFIGURATION ======= (Modifiez ces valeurs selon vos besoins)
DATA_DIR="training_data"        # Dossier contenant vos CSV/JSON
MODEL_NAME="deepseek-ai/deepseek-coder-1.3b-base"  # Modèle à fine-tuner
EPOCHS=3                        # Nombre d'époques d'entraînement
BATCH_SIZE=4                    # Taille de batch (2-8 selon RAM)
# =============================

echo "🚀 Démarrage du processus de fine-tuning DeepSeek sur $(sw_vers -productName) $(sw_vers -productVersion)"

# Créer l'environnement virtuel
echo "\n🔧 Création de l'environnement Python..."
python3 -m venv deepseek-env
source deepseek-env/bin/activate

# Installer les dépendances avec optimisation MPS
echo "\n📦 Installation des dépendances (peut prendre 5-10 min)..."
pip install --upgrade pip > /dev/null
pip install torch transformers datasets accelerate peft bitsandbytes pandas pyarrow > /dev/null

# Vérifier la compatibilité MPS
echo "\n🔍 Vérification de la compatibilité GPU:"
python -c "import torch; print(f'► MPS disponible: {torch.backends.mps.is_available()}\n► MPS activé: {torch.backends.mps.is_built()}')"

# Générer le script d'entraînement
echo "\n🛠️ Génération du script d'entraînement..."
cat > deepseek_train.py <<EOL
import os
import pandas as pd
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model
import torch

# Configuration
model_id = "$MODEL_NAME"
data_path = "$DATA_DIR"
output_dir = "./deepseek_finetuned"
os.makedirs(output_dir, exist_ok=True)

# 1. Chargement des données
print("\\n📂 Chargement des données...")
dfs = []
for file in os.listdir(data_path):
    if file.endswith('.csv'):
        dfs.append(pd.read_csv(f"{data_path}/{file}"))
    elif file.endswith('.json'):
        dfs.append(pd.read_json(f"{data_path}/{file}"))

if not dfs:
    raise ValueError("Aucune donnée trouvée! Vérifiez le dossier $DATA_DIR")

dataset = Dataset.from_pandas(pd.concat(dfs))

# 2. Préparation du tokenizer
print("🔡 Initialisation du tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_id)
tokenizer.pad_token = tokenizer.eos_token

def tokenize_function(examples):
    return tokenizer(
        examples["text"],  # Colonne contenant le texte
        padding="max_length",
        truncation=True,
        max_length=512
    )

tokenized_dataset = dataset.map(tokenize_function, batched=True)

# 3. Configuration 4-bit QLoRA
print("⚙️ Configuration du modèle (4-bit QLoRA)...")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16
)

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=bnb_config,
    device_map="auto",
    use_mps_device=True
)

# 4. Paramètres LoRA
peft_config = LoraConfig(
    r=8,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    task_type="CAUSAL_LM"
)
model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

# 5. Entraînement
print("🚂 Lancement de l'entraînement (peut prendre du temps)...")
training_args = TrainingArguments(
    output_dir=output_dir,
    num_train_epochs=$EPOCHS,
    per_device_train_batch_size=$BATCH_SIZE,
    gradient_accumulation_steps=4,
    learning_rate=2e-5,
    optim="paged_adamw_8bit",
    fp16=True,
    logging_steps=10,
    use_mps_device=True,
    report_to="none",
    save_strategy="epoch"
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
)

trainer.train()

# 6. Sauvegarde finale
print("💾 Sauvegarde du modèle fine-tuné...")
model.save_pretrained(f"{output_dir}/final_model")
print(f"✅ Entraînement terminé! Modèle sauvegardé dans: {output_dir}/final_model")
EOL

# Lancer l'entraînement
echo "\n🧠 Début de l'entraînement du modèle (GPU MPS activé)..."
echo "► Modèle: $MODEL_NAME"
echo "► Epochs: $EPOCHS"
echo "► Taille de batch: $BATCH_SIZE"
echo "► Données: $DATA_DIR\n"

python deepseek_train.py

echo "\n✨ Opération terminée! Utilisez 'source deepseek-env/bin/activate' pour activer l'environnement"
```

### Comment utiliser ce script :

1. **Enregistrez le script** dans un fichier `run_deepseek_train.zsh`
2. **Rendez-le exécutable** :
   ```zsh
   chmod +x run_deepseek_train.zsh
   ```
3. **Préparez vos données** :
   - Créez un dossier `training_data`
   - Placez vos fichiers CSV/JSON dedans
   - Assurez-vous qu'ils contiennent une colonne "text"
4. **Exécutez le script** :
   ```zsh
   ./run_deepseek_train.zsh
   ```

### Fonctionnalités clés :

1. ✅ Installation automatique des dépendances
2. ✅ Optimisation GPU MPS pour Apple Silicon
3. ✅ Support des formats CSV et JSON
4. ✅ Quantification 4-bit (QLoRA) pour économie mémoire
5. ✅ Sauvegarde automatique du modèle final
6. ✅ Rapport de progression en temps réel

### Configuration modifiable :

```zsh
# Dans la section CONFIGURATION :
DATA_DIR="votre_dossier_data"   # Dossier contenant les données
MODEL_NAME="deepseek-ai/deepseek-llm-7b-base"  # Modèle plus grand
EPOCHS=5                        # Plus d'époches
BATCH_SIZE=2                    # Batch plus petit si mémoire limitée
```

Pour un modèle plus performant mais plus gourmand, remplacez par :
```zsh
MODEL_NAME="deepseek-ai/deepseek-llm-7b-base"
```

Ce script est optimisé pour fonctionner sur MacBook Pro M2/M3 avec 16Go+ de RAM. Le processus peut prendre plusieurs heures selon la quantité de données et la puissance de votre machine.
