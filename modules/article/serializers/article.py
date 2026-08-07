from rest_framework.serializers import ModelSerializer
from modules.article.models import Article, ArticleCategory, ArticleTagRelation, ArticleTag
from modules.user.models import Users


class ArticleSerializers(ModelSerializer):
    class Meta:
        model = Article
        field = "__all__"
        exclude = []

    def to_representation(self, obj):  # 此函数在序列化时才会用到，用于自定义输出
        cata_obj = None
        cata_father_obj = None
        ret = super(ArticleSerializers, self).to_representation(obj)
        if obj.category:
            cata_obj = ArticleCategory.objects.get(id=obj.category)
            cata_father_obj = ArticleCategory.objects.get(id=cata_obj.father)
        user_obj = Users.objects.get(id=obj.author)
        tag_id_list = ArticleTagRelation.objects.filter(article=obj.id)
        tag_obj_list = []
        for tag_id in tag_id_list:
            tag_obj = ArticleTag.objects.get(id=tag_id.tag)
            tag_obj_list.append(tag_obj)
        ret["category"] = {
            "id": cata_obj.id,
            "name": cata_obj.name,
            "father": cata_father_obj.name
        } if cata_obj else None
        ret["author"] = {
            "name": user_obj.nickName,
            'id': user_obj.id,
            'avatar': user_obj.avatar
        }
        ret["tags"] = tag_obj_list
        return ret
