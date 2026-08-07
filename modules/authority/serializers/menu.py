from rest_framework.serializers import ModelSerializer

from modules.authority.models import Menu


class MenuSerializers(ModelSerializer):
    class Meta:
        model = Menu
        field = "__all__"
        exclude = []
        depth = 0

    def to_representation(self, obj):  # 此函数在序列化时才会用到，用于自定义输出
        ret = super(MenuSerializers, self).to_representation(obj)
        if obj.father:
            ret["fatherName"] = Menu.objects.get(id=obj.father).name
        else:
            ret["fatherName"] = None
        return ret
