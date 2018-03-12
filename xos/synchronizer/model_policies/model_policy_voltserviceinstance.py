
# Copyright 2017-present Open Networking Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from synchronizers.new_base.modelaccessor import VOLTServiceInstance, ServiceInstanceLink, VSGService, VSGServiceInstance, model_accessor
from synchronizers.new_base.policy import Policy

class VOLTServiceInstancePolicy(Policy):
    model_name = "VOLTServiceInstance"

    def handle_create(self, tenant):
        return self.handle_update(tenant)

    def handle_update(self, tenant):

        if (tenant.link_deleted_count > 0) and (not tenant.provided_links.exists()):
            # If this instance has no links pointing to it, delete
            self.handle_delete(tenant)
            if VOLTServiceInstance.objects.filter(id=tenant.id).exists():
                tenant.delete()
            return

        self.manage_vsg(tenant)
        self.cleanup_orphans(tenant)

    def handle_delete(self, tenant):
        pass
        # assume this is handled by ServiceInstanceLink being deleted
        #if tenant.vcpe:
        #    tenant.vcpe.delete()

    def get_current_vsg(self, tenant):
        for link in ServiceInstanceLink.objects.filter(subscriber_service_instance_id = tenant.id):
            # NOTE: Assumes the first (and only?) link is to a vsg
            # cast from ServiceInstance to VSGTenant
            return link.provider_service_instance.leaf_model
        return None

    def create_eastbound_instance(self, si):

        chain = si.subscribed_links.all()

        # Already has a chain
        if len(chain) > 0 and not si.is_new:
            self.logger.debug("MODEL_POLICY: Subscriber %s is already part of a chain" % si.id)
            return

        # if it does not have a chain,
        # Find links to the next element in the service chain
        # and create one

        links = si.owner.subscribed_dependencies.all()

        for link in links:
            si_class = link.provider_service.get_service_instance_class_name()
            self.logger.info("MODEL_POLICY: VOLTServiceInstance %s creating %s" % (si, si_class))

            eastbound_si_class = model_accessor.get_model_class(si_class)
            eastbound_si = eastbound_si_class()
            eastbound_si.creator = si.creator
            eastbound_si.owner_id = link.provider_service_id
            eastbound_si.save()
            link = ServiceInstanceLink(provider_service_instance=eastbound_si, subscriber_service_instance=si)
            link.save()

    def manage_vsg(self, tenant):
        # Each VOLT object owns exactly one VCPE object

        if tenant.deleted:
            self.logger.info("MODEL_POLICY: VOLTServiceInstance %s deleted, deleting vsg" % tenant)
            return

        cur_vsg = self.get_current_vsg(tenant)

        # Check to see if the wrong s-tag is set. This can only happen if the
        # user changed the s-tag after the VOLTServiceInstance object was created.
        if cur_vsg and cur_vsg.instance:
            s_tags = Tag.objects.filter(content_type=cur_vsg.instance.self_content_type_id,
                                        object_id=cur_vsg.instance.id, name="s_tag")
            if s_tags and (s_tags[0].value != str(tenant.s_tag)):
                self.logger.info("MODEL_POLICY: VOLTServiceInstance %s s_tag changed, deleting vsg" % tenant)
                cur_vsg.delete()
                cur_vsg = None

        if cur_vsg is None:
            self.create_eastbound_instance(tenant)

    def cleanup_orphans(self, tenant):
        # ensure vOLT only has one vCPE
        cur_vsg = self.get_current_vsg(tenant)

        links = tenant.subscribed_links.all()
        for link in links:
            if (link.provider_service_instance_id != cur_vsg.id):
                link.delete()
