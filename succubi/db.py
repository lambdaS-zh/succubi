class ImageDb(object):

    def __init__(self):
        pass

    def add(self, image_id, repo, tag, size):
        raise NotImplementedError()

    def list(self, repo_tag=None):
        # Each item contains fields by order:
        #  image_id, repo, tag, size, timestamp
        pass

    def get_by_id(self, image_id):
        raise NotImplementedError()

    def get_by_repo_tag(self, repo_tag):
        raise NotImplementedError()

    def delete_by_id(self, image_id):
        raise NotImplementedError()

    def delete_by_repo_tag(self, repo_tag):
        raise NotImplementedError()
