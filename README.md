# Damaged Area Detection from Satellite Images After Natural Disasters

## Project Overview
This project, developed by students of Yıldız Technical University's Computer Engineering Department, aims to leverage deep learning techniques for detecting damaged areas in satellite images post-natural disasters. By classifying images into four categories—Destroyed, Major, Minor, and No Damage—we provide a crucial tool for emergency response teams to prioritize their efforts effectively.

## The Challenge
Natural disasters leave behind a trail of devastation, making rapid response critical to saving lives. Traditional methods of assessing damage are slow and labor-intensive. Our solution uses the U-Net deep learning model to automate the classification of damage, significantly reducing response times.

## Our Solution
We employed U-Net, a convolutional network designed for quick and precise image segmentation. Our model was trained on a dataset of satellite images taken from the 06.02.2023 earthquake, labeled with varying degrees of damage. This approach allowed us to identify affected areas with a notable degree of accuracy.

## Methodology
- **Data Preparation**: Satellite images were labeled with four distinct categories of damage using Label Studio, then converted to a machine-readable format.
- **Model Training**:  We trained our U-Net model on this dataset, utilizing both raw and labeled images to enhance its predictive accuracy.
- **Optimization**: Through rigorous testing and optimization, including the innovative application of binary mode, we improved our model's Intersection over Union (IoU) score significantly.

## Impact
Our project stands out by providing emergency response teams with actionable insights, enabling them to allocate resources where they are needed most urgently. This could potentially save lives by focusing efforts on areas suffering from severe damage.

## Acknowledgments
We extend our deepest gratitude to Prof. Dr. Mine Elif KARSLIGİL for her guidance and support throughout this project, and to all faculty members who have contributed to our education.

## Future Directions
While our model demonstrates promising results, future work will focus on refining its accuracy, expanding the dataset, and integrating real-time analysis capabilities for even faster response times post-disaster.

## Contact
For more information or to discuss potential collaborations, please contact us at [yusuftahakara@gmail.com].

---
*This project is a part of the Computer Engineering curriculum at Yildiz Technical University. We extend our gratitude to all contributors and our advisor for their invaluable support.*
