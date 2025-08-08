import torch
import torchvision.transforms as transforms

from PIL import Image
from torchvision.models import squeezenet1_0
from sklearn.metrics.pairwise import cosine_similarity

def cosine_similarity_function(feature_vector_a, feature_vector_b):
    # 余弦相似度计算
    if feature_vector_a.is_cuda:
        feature_vector_a = feature_vector_a.cpu().numpy()
    if feature_vector_b.is_cuda:
        feature_vector_b = feature_vector_b.cpu().numpy()
    similarity = cosine_similarity(feature_vector_a.reshape(1, -1), feature_vector_b.reshape(1, -1))
    return similarity[0, 0]

CUT_SIDE = 0.02
IMG_SIZE = 29

# 图片预处理
def preprocess_image(image:Image.Image,targetsize:int):
    l,h = image.getbbox()[2:]
    if l>h:
        side = int(h*CUT_SIDE)
        upcrop = (l-h)//2
        downcrop = l-h-upcrop
        image = image.crop((upcrop+side,side,l-downcrop-side,h-side))
    else:
        side = int(l*0.05)
        upcrop = (h-l)//2
        downcrop = h-l-upcrop
        image = image.crop((side,upcrop+side,l-side,h-downcrop-side))
    transform = transforms.Compose([
        transforms.Resize((targetsize, targetsize)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    input_tensor = transform(image)
    input_batch = input_tensor.unsqueeze(0)
    return input_batch

# 提取特征向量
def extract_features(image:Image.Image, model,target_size:int):
    input_batch = preprocess_image(image,target_size)
    device = torch.device("cpu") #("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    input_batch = input_batch.to(device)
    with torch.no_grad():
        features = model(input_batch)
    return features


squeezenet_model = squeezenet1_0(pretrained=True)
squeezenet_model.eval()
loaded_features = torch.load("src/static/others/squeezenet_features.pt")

def find_cover_id(image:Image.Image)->int:
    img_feature = extract_features(image, squeezenet_model,target_size=IMG_SIZE)
    temp_id = -1
    temp_similarity = 0
    for img_id, feature in loaded_features.items():
        similarity = cosine_similarity_function(img_feature, feature)
        if similarity > temp_similarity:
            temp_similarity = similarity
            temp_id = img_id
    return temp_id