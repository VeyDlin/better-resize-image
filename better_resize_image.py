from typing import Literal
from PIL import Image


from invokeai.app.services.image_records.image_records_common import ImageCategory, ResourceOrigin
from invokeai.app.invocations.baseinvocation import (
    BaseInvocation,
    InputField,
    invocation,
    InvocationContext,
    WithMetadata,
    WithWorkflow,
)

from invokeai.app.invocations.primitives import (
    ImageField,
    ImageOutput
)


PIL_RESAMPLING_MODES = Literal[
    "nearest",
    "box",
    "bilinear",
    "hamming",
    "bicubic",
    "lanczos",
]


PIL_RESAMPLING_MAP = {
    "nearest": Image.Resampling.NEAREST,
    "box": Image.Resampling.BOX,
    "bilinear": Image.Resampling.BILINEAR,
    "hamming": Image.Resampling.HAMMING,
    "bicubic": Image.Resampling.BICUBIC,
    "lanczos": Image.Resampling.LANCZOS,
}

RESIZE_MODES = Literal[
    "fill",
    "stretch",
    "fit",
    "center",
    "crop",
]


@invocation(
    "better_image_resize",
    title="Better resize Image",
    tags=["image", "resize"],
    category="image",
    version="1.0.0",
)
class BetterResizeImageInvocation(BaseInvocation, WithMetadata, WithWorkflow):
    """Resizes an image to specific dimensions"""
    image: ImageField = InputField(default=None, description="Image to be resize")
    width: int = InputField(default=512., description="The width to resize to (px)")
    height: int = InputField(default=512., description="The height to resize to (px)")
    resample_mode: PIL_RESAMPLING_MODES = InputField(default="bicubic", description="The resampling mode")
    resize_mod: RESIZE_MODES = InputField(default="fit", description="The resize mode")



    def invoke(self, context: InvocationContext) -> ImageOutput:
        RESIZE_MODES_MAP = {
            "fill": self.fill,
            "stretch": self.stretch,
            "fit": self.fit,
            "center": self.center,
            "crop": self.crop,
        }

        image = context.services.images.get_pil_image(self.image.image_name)
        resample_mode = PIL_RESAMPLING_MAP[self.resample_mode]
        image_resize = RESIZE_MODES_MAP[self.resize_mod]

        image_out = image_resize(resample_mode, image)

        image_dto = context.services.images.create(
            image=image_out,
            image_origin=ResourceOrigin.INTERNAL,
            image_category=ImageCategory.GENERAL,
            node_id=self.id,
            session_id=context.graph_execution_state_id,
            is_intermediate=self.is_intermediate,
            workflow=self.workflow,
        )

        return ImageOutput(
            image=ImageField(image_name=image_dto.image_name),
            width=image_dto.width,
            height=image_dto.height,
        )
        


    def fill(self, resample_mode, image):
        original_width, original_height = image.size
        
        width_ratio = self.width / original_width
        height_ratio = self.height / original_height
        
        resize_ratio = max(width_ratio, height_ratio)
        
        new_width = int(original_width * resize_ratio)
        new_height = int(original_height * resize_ratio)
        resized_image = image.resize((new_width, new_height), resample_mode)
        
        final_image = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        final_image.paste(resized_image, ((self.width - new_width) // 2, (self.height - new_height) // 2))
        
        return final_image
    


    def stretch(self, resample_mode, image):
        final_image = image.resize((self.width, self.height), resample_mode)
        
        return final_image
    


    def fit(self, resample_mode, image):
        original_width, original_height = image.size

        resize_ratio = original_width / original_height
        width = self.width
        height = self.height

        if (width / height) < resize_ratio:
            height = int(width / resize_ratio)
        else:
            width = int(height * resize_ratio)

        final_image = image.resize((width, height), resample_mode)
        
        return final_image



    def center(self, resample_mode, image):
        original_width, original_height = image.size

        width_ratio = self.width / original_width
        height_ratio = self.height / original_height
        scale_ratio = min(width_ratio, height_ratio)

        new_width = int(scale_ratio * original_width)
        new_height = int(scale_ratio * original_height)

        resized_image = image.resize((new_width, new_height), resample_mode)

        final_image = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))

        x = (self.width - new_width) // 2
        y = (self.height - new_height) // 2

        final_image.paste(resized_image, (x, y))

        return final_image
    


    def crop(self, resample_mode, image):
        original_width, original_height = image.size
        
        final_image = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))

        x = (self.width - original_width) // 2
        y = (self.height - original_height) // 2

        final_image.paste(image, (x, y))

        return final_image