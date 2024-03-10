# -*- coding: utf-8 -*-
"""gui.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1xe1_wJyVb96OPaIhmneEbt4f3-gExZH5
"""

!pip install -U segmentation-models

!pip install keras==2.3.1

!pip install tensorflow --upgrade

!pip install keras

import os
os.environ["SM_FRAMEWORK"] = "tf.keras"

from tensorflow import keras
import segmentation_models as sm

!pip install -U albumentations>=0.3.0 --user
!pip install -U --pre segmentation-models --user

!pip install ipywidgets ipyfilechooser

from google.colab import drive
drive.mount("/content/drive", force_remount=True)

from ipywidgets import widgets, VBox, HBox
from IPython.display import display
from ipyfilechooser import FileChooser
import cv2
import matplotlib.pyplot as plt
from google.colab import drive
drive.mount("/content/drive", force_remount=True)

import os
import cv2
import keras
import numpy as np
import matplotlib.pyplot as plt
import segmentation_models as sm
import albumentations as A

# Data directory on Google Drive
DATA_DIR = '/content/drive/My Drive/'

# Update paths for training, validation, and test sets
x_train_dir = os.path.join(DATA_DIR, 'train/images')
y_train_dir = os.path.join(DATA_DIR, 'train/masks')

x_valid_dir = os.path.join(DATA_DIR, 'val/images')
y_valid_dir = os.path.join(DATA_DIR, 'val/masks')

x_test_dir = os.path.join(DATA_DIR, 'test/images')
y_test_dir = os.path.join(DATA_DIR, 'test/masks')


# Our helper function used for visualizing images
def visualize(**images):
    """Plot images in one row."""
    n = len(images)
    plt.figure(figsize=(16, 5))
    for i, (name, image) in enumerate(images.items()):
        plt.subplot(1, n, i + 1)
        plt.xticks([])
        plt.yticks([])
        plt.title(' '.join(name.split('_')).title())
        plt.imshow(image)
    plt.show()

# Dataset class
class Dataset:
    def __init__(self, images_dir, masks_dir, classes=None, augmentation=None, preprocessing=None):
        self.ids = os.listdir(images_dir)
        self.images_fps = [os.path.join(images_dir, image_id) for image_id in self.ids]
        self.masks_fps = [os.path.join(masks_dir, image_id) for image_id in self.ids]
        self.class_values = {cls.lower(): idx for idx, cls in enumerate(classes)}
        self.augmentation = augmentation
        self.preprocessing = preprocessing

    def __getitem__(self, i):
        image = cv2.imread(self.images_fps[i])
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (320, 320))

        mask = np.zeros((image.shape[0], image.shape[1], len(self.class_values)), dtype=np.uint8)

        for cls, idx in self.class_values.items():
            if cls.lower() == 'minor':
                cls = 'no damage'  # Minor'u No Damage olarak kabul et
            elif cls.lower() == 'major':
                cls = 'damaged'  # Major'u Damage olarak kabul et

            cls_mask = cv2.imread(self.masks_fps[i], cv2.IMREAD_COLOR)
            cls_mask = cv2.resize(cls_mask, (320, 320))
            mask[..., idx] = (cls_mask == np.array(eval(cls))[None, None, :]).all(axis=-1).astype('uint8')

        if self.augmentation:
            sample = self.augmentation(image=image, mask=mask)
            image, mask = sample['image'], sample['mask']

        if self.preprocessing:
            sample = self.preprocessing(image=image, mask=mask)
            image, mask = sample['image'], sample['mask']

        return image, mask.astype('float32')

    def __len__(self):
        return len(self.ids)

# Dataloader
class Dataloader(keras.utils.Sequence):
    def __init__(self, dataset, batch_size=1, shuffle=False):
        self.dataset = dataset
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.indexes = np.arange(len(dataset))

        self.on_epoch_end()

    def __getitem__(self, i):
        start = i * self.batch_size
        stop = (i + 1) * self.batch_size
        data = [self.dataset[j] for j in range(start, stop)]

        images = [item[0] for item in data]
        masks = [item[1] for item in data]

        batch = [np.stack(images, axis=0), np.stack(masks, axis=0)]
        return batch

    def __len__(self):
        return len(self.indexes) // self.batch_size

    def on_epoch_end(self):
        if self.shuffle:
            self.indexes = np.random.permutation(self.indexes)

# Input dimensions
INPUT_HEIGHT = 512
INPUT_WIDTH = 512
CHANNELS = 3

# Specify data preprocessing functions
def get_preprocessing(preprocessing_fn=None):
    if preprocessing_fn:
        _transform = [
            A.Lambda(image=preprocessing_fn),
        ]
    else:
        _transform = []

    return A.Compose(_transform)

# Specify augmentation functions for training
def get_training_augmentation():
    train_transform = [
        A.HorizontalFlip(p=0.5),
        A.ShiftScaleRotate(scale_limit=0.5, rotate_limit=0, shift_limit=0.1, p=1, border_mode=0),
        A.PadIfNeeded(min_height=INPUT_HEIGHT, min_width=INPUT_WIDTH, always_apply=True, border_mode=0),
        A.RandomCrop(height=INPUT_HEIGHT, width=INPUT_WIDTH, always_apply=True),
        A.IAAAdditiveGaussianNoise(p=0.2),
        A.IAAPerspective(p=0.5),
        A.OneOf(
            [
                A.CLAHE(p=1),
                A.RandomBrightness(p=1),
                A.RandomGamma(p=1),
            ],
            p=0.9,
        ),
        A.OneOf(
            [
                A.IAASharpen(p=1),
                A.Blur(blur_limit=3, p=1),
                A.MotionBlur(blur_limit=3, p=1),
            ],
            p=0.9,
        ),
        A.OneOf(
            [
                A.RandomContrast(p=1),
                A.HueSaturationValue(p=1),
            ],
            p=0.9,
        ),
    ]
    return A.Compose(train_transform)

# Create an instance of the training dataset
damage_classes = ['(0, 255, 0)', '(0, 255, 255)', '(255, 0, 0)', '(0, 0, 255)']
train_dataset = Dataset(x_train_dir, y_train_dir, classes=damage_classes, augmentation=None,
                        preprocessing=get_preprocessing())

# Create an instance of the validation dataset
valid_dataset = Dataset(x_valid_dir, y_valid_dir, classes=damage_classes, augmentation=None,
                        preprocessing=get_preprocessing())

# Define UNet model
BACKBONE = 'efficientnetb3'
CLASSES = ['No Damage', 'Minor', 'Major', 'Damaged']
LR = 0.0001
EPOCHS = 100
BATCH_SIZE = 8

# Create the UNet model
model = sm.Unet(BACKBONE, classes=len(CLASSES), activation='softmax', input_shape=(INPUT_HEIGHT, INPUT_WIDTH, CHANNELS))

# Define optimizer and loss functions
optim = keras.optimizers.Adam(LR)

# Loss functions
dice_loss = sm.losses.DiceLoss()
focal_loss = sm.losses.CategoricalFocalLoss()
total_loss = dice_loss + (1 * focal_loss)

# Metrics
metrics = [sm.metrics.IOUScore(name='iou_score', threshold=0.5), sm.metrics.FScore(name='f1-score', threshold=0.5)]

# Compile the model
model.compile(optim, total_loss, metrics)

# Create dataloaders
train_dataloader = Dataloader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
valid_dataloader = Dataloader(valid_dataset, batch_size=BATCH_SIZE, shuffle=False)

# Model Checkpoint, save the best weights to Google Drive
model_checkpoint = keras.callbacks.ModelCheckpoint(
    '/content/drive/My Drive/best_model.h5',
    save_weights_only=True,
    save_best_only=True,
    monitor='val_iou_score',
    mode='max',
)

# Learning Rate Reduction
lr_reduce = keras.callbacks.ReduceLROnPlateau(
    monitor='val_loss',
    factor=0.1,
    patience=5,
    min_lr=0.00001,
    verbose=1,
)


# Create a file chooser for selecting the model file
model_chooser = FileChooser('/content/drive/MyDrive/', title='Select Model File:')
model_chooser.use_dir_icons = True
model_chooser.filter_pattern = '*.h5'

# Create a file chooser for selecting the test images directory
test_chooser = FileChooser('/content/drive/MyDrive/', title='Select Test Images Directory:')
test_chooser.use_dir_icons = True
test_chooser.default_path = '/content/drive/MyDrive/test/images'

# Create a button for triggering the prediction
predict_button = widgets.Button(description='Predict')

# Output widget for displaying results
output_widget = widgets.Output()

def predict_button_clicked(b):
    # Load the selected model
    model_path = model_chooser.selected
    model = sm.Unet(BACKBONE, classes=len(CLASSES), activation='softmax', input_shape=(INPUT_HEIGHT, INPUT_WIDTH, CHANNELS))
    model.load_weights(model_path)

    # Get the selected test images directory
    test_dir = test_chooser.selected

    # Assuming images and masks are in separate directories inside the test directory
    images_dir = os.path.join(test_dir, 'images')
    masks_dir = os.path.join(test_dir, 'masks')

    # Create an instance of the test dataset
    test_dataset = Dataset(
        images_dir,
        masks_dir,
        classes=damage_classes,
        augmentation=get_training_augmentation(),
        preprocessing=get_preprocessing()
    )

    # Number of random samples to visualize (changed to 5)
    n = 20

    # Randomly select 'n' indices from the test dataset
    ids = np.random.choice(np.arange(len(test_dataset)), size=n)

    # Create a figure to display the results
    plt.figure(figsize=(20, 8 * n))

    # Loop over selected test samples and make predictions
    for i, sample_idx in enumerate(ids):
        image, gt_mask = test_dataset[sample_idx]
        image = cv2.resize(image, (INPUT_WIDTH, INPUT_HEIGHT))
        image = np.expand_dims(image, axis=0)
        pr_mask = model.predict(image)

        # Resize ground truth mask for display
        gt_mask_resized = cv2.resize(gt_mask, (INPUT_WIDTH, INPUT_HEIGHT))

        # Specify class colors
        colors = [(0, 255, 0), (255, 0, 0)]  # Green for "No Damage", Red for "Damaged"

        # Show the original image
        plt.subplot(n, 6, i * 6 + 1)
        plt.imshow(image.squeeze())
        plt.title('Original Image')

        # Show the ground truth mask for 'No Damage' class
        gt_mask_no_damage = gt_mask_resized[..., damage_classes.index('(0, 255, 0)')].squeeze()
        overlay_gt_no_damage = image.squeeze().copy()
        overlay_gt_no_damage[gt_mask_no_damage > 0] = colors[0]
        plt.subplot(n, 6, i * 6 + 2)
        plt.imshow(overlay_gt_no_damage)
        plt.title('GT No Damage Mask')

        # Show the predicted mask for 'No Damage' class
        pr_mask_no_damage = (pr_mask[..., damage_classes.index('(0, 255, 0)')] > 0.5).astype(np.uint8).squeeze()
        overlay_pr_no_damage = image.squeeze().copy()
        overlay_pr_no_damage[pr_mask_no_damage > 0] = colors[0]
        plt.subplot(n, 6, i * 6 + 3)
        plt.imshow(overlay_pr_no_damage)
        plt.title('Pred No Damage Mask')

        # Show the ground truth mask for 'Damaged' class
        gt_mask_damaged = gt_mask_resized[..., damage_classes.index('(255, 0, 0)')].squeeze()
        overlay_gt_damaged = image.squeeze().copy()
        overlay_gt_damaged[gt_mask_damaged > 0] = colors[1]
        plt.subplot(n, 6, i * 6 + 4)
        plt.imshow(overlay_gt_damaged)
        plt.title('GT Damaged Mask')

        # Show the predicted mask for 'Damaged' class
        pr_mask_damaged = (pr_mask[..., damage_classes.index('(255, 0, 0)')] > 0.5).astype(np.uint8).squeeze()
        overlay_pr_damaged = image.squeeze().copy()
        overlay_pr_damaged[pr_mask_damaged > 0] = colors[1]
        plt.subplot(n, 6, i * 6 + 5)
        plt.imshow(overlay_pr_damaged)
        plt.title('Pred Damaged Mask')

    plt.show()

# Attach the callback function to the button
predict_button.on_click(predict_button_clicked)






# Arrange the widgets in a layout
layout = VBox([
    HBox([model_chooser, test_chooser]),
    predict_button,
    output_widget
])

# Display the layout
display(layout)

from sklearn.metrics import confusion_matrix
import seaborn as sns
# Create an instance of the test dataset
test_dataset = Dataset(
    x_test_dir,
    y_test_dir,
    classes=damage_classes,
    augmentation=None,  # Use training augmentation for testing as well
    preprocessing=get_preprocessing()
)

# Create test dataloader
test_dataloader = Dataloader(test_dataset, batch_size=1, shuffle=False)

# Make predictions on the entire test dataset
y_true = []
y_pred = []

for i in range(len(test_dataset)):
    image, gt_mask = test_dataset[i]
    image = cv2.resize(image, (512, 512))  # Boyutları 512'ye ayarla
    image = np.expand_dims(image, axis=0)
    pr_mask = model.predict(image)

    # Convert one-hot encoded predictions to class indices
    pred_class = np.argmax(pr_mask, axis=-1).flatten()
    true_class = np.argmax(gt_mask, axis=-1).flatten()

    y_true.extend(true_class.tolist())
    y_pred.extend(pred_class.tolist())

# Ensure consistent lengths
y_true = np.array(y_true)
y_pred = np.array(y_pred)

# Check if lengths are consistent
if len(y_true) != len(y_pred):
    raise ValueError("Inconsistent lengths between y_true and y_pred.")

# Create confusion matrix
cm = confusion_matrix(y_true, y_pred)

# Plot confusion matrix as a heatmap
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=CLASSES, yticklabels=CLASSES)
plt.xlabel('Predicted')
plt.ylabel('True')
plt.title('Confusion Matrix')
plt.show()

from sklearn.metrics import confusion_matrix
import seaborn as sns

# Create an instance of the test dataset
test_dataset = Dataset(
    x_test_dir,
    y_test_dir,
    classes=damage_classes,
    augmentation=get_training_augmentation(),
    preprocessing=get_preprocessing()
)

# Create test dataloader
test_dataloader = Dataloader(test_dataset, batch_size=1, shuffle=False)

# Make predictions on the entire test dataset
y_true = []
y_pred = []

for i in range(len(test_dataset)):
    image, gt_mask = test_dataset[i]
    image = cv2.resize(image, (512, 512))  # Boyutları 512'ye ayarla
    image = np.expand_dims(image, axis=0)
    pr_mask = model.predict(image)

    # Convert one-hot encoded predictions to class indices
    pred_class = np.argmax(pr_mask, axis=-1).flatten()
    true_class = np.argmax(gt_mask, axis=-1).flatten()

    y_true.extend(true_class.tolist())
    y_pred.extend(pred_class.tolist())

# Ensure consistent lengths
y_true = np.array(y_true)
y_pred = np.array(y_pred)

# Check if lengths are consistent
if len(y_true) != len(y_pred):
    raise ValueError("Inconsistent lengths between y_true and y_pred.")

# Extract indices for "No Damage" and "Damage" classes
no_damage_index = damage_classes.index('(0, 255, 0)')
damage_index = damage_classes.index('(255, 0, 0)')

# Select relevant rows and columns from the confusion matrix
cm = confusion_matrix(y_true, y_pred)
cm_subset = cm[[no_damage_index, damage_index]][:, [no_damage_index, damage_index]]

# Plot confusion matrix as a heatmap
plt.figure(figsize=(8, 6))
sns.heatmap(cm_subset, annot=True, fmt='d', cmap='Blues', xticklabels=['No Damage', 'Damage'], yticklabels=['No Damage', 'Damage'])
plt.xlabel('Predicted')
plt.ylabel('True')
plt.title('Confusion Matrix')
plt.show()

from sklearn.metrics import accuracy_score
import seaborn as sns

# Create an instance of the test dataset
test_dataset = Dataset(
    x_test_dir,
    y_test_dir,
    classes=damage_classes,
    augmentation=get_training_augmentation(),
    preprocessing=get_preprocessing()
)

# Create test dataloader
test_dataloader = Dataloader(test_dataset, batch_size=1, shuffle=False)

# Make predictions on the entire test dataset
y_true = []
y_pred = []

for i in range(len(test_dataset)):
    image, gt_mask = test_dataset[i]
    image = cv2.resize(image, (512, 512))  # Boyutları 512'ye ayarla
    image = np.expand_dims(image, axis=0)
    pr_mask = model.predict(image)

    # Convert one-hot encoded predictions to class indices
    pred_class = np.argmax(pr_mask, axis=-1).flatten()
    true_class = np.argmax(gt_mask, axis=-1).flatten()

    y_true.extend(true_class.tolist())
    y_pred.extend(pred_class.tolist())

# Ensure consistent lengths
y_true = np.array(y_true)
y_pred = np.array(y_pred)

# Check if lengths are consistent
if len(y_true) != len(y_pred):
    raise ValueError("Inconsistent lengths between y_true and y_pred.")

# Extract indices for "No Damage" and "Damage" classes
no_damage_index = damage_classes.index('(0, 255, 0)')
damage_index = damage_classes.index('(255, 0, 0)')

# Select relevant rows and columns from the confusion matrix
cm = confusion_matrix(y_true, y_pred)
cm_subset = cm[[no_damage_index, damage_index]][:, [no_damage_index, damage_index]]

# Calculate accuracy score
accuracy = accuracy_score(y_true, y_pred)

# Print the accuracy score
print(f'Accuracy Score: {accuracy}')

# Plot confusion matrix as a heatmap
plt.figure(figsize=(8, 6))
sns.heatmap(cm_subset, annot=True, fmt='d', cmap='Blues', xticklabels=['No Damage', 'Damage'], yticklabels=['No Damage', 'Damage'])
plt.xlabel('Predicted')
plt.ylabel('True')
plt.title('Confusion Matrix')
plt.show()