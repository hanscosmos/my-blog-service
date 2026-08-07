from rest_framework.serializers import ModelSerializer
from modules.article.models import ArticleCategory


class ArticleCategorySerializers(ModelSerializer):
    class Meta:
        model = ArticleCategory
        field = "__all__"
        exclude = []
        depth = 0

    def to_representation(self, obj):  # 此函数在序列化时才会用到，用于自定义输出
        ret = super(ArticleCategorySerializers, self).to_representation(obj)
        if obj.father:
            ret["fatherName"] = ArticleCategory.objects.get(id=obj.father).name
        else:
            ret["fatherName"] = None
        return ret
