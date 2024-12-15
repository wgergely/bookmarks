__all__ = ['TemplateError', 'TemplateMetadataError', 'TemplateSizeError', 'TemplateLinkExistsError']


class TemplateError(Exception):
    pass


class TemplateMetadataError(TemplateError):
    pass


class TemplateSizeError(TemplateError):
    pass


class TemplateLinkExistsError(TemplateError):
    pass
