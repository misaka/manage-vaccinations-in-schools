# frozen_string_literal: true

# == Schema Information
#
# Table name: contacts
#
#  id           :bigint           not null, primary key
#  email        :string
#  name         :string           not null
#  phone        :string
#  relationship :enum             not null
#  source       :enum             not null
#  type         :enum             not null
#  created_at   :datetime         not null
#  updated_at   :datetime         not null
#  patient_id   :bigint           not null
#
# Indexes
#
#  index_contacts_on_patient_id  (patient_id)
#
# Foreign Keys
#
#  fk_rails_...  (patient_id => patients.id)
#

class Contact < ApplicationRecord
  belongs_to :patient

  validates :name, presence: true
  validates :relationship, presence: true
  validates :source, presence: true
  validates :type, presence: true

  validates :email, notify_safe_email: { allow_blank: true }

  # validates :email, uniqueness: { scope: :patient_id }, allow_blank: true
  # validates :phone, uniqueness: { scope: :patient_id }, allow_blank: true
  validates :phone,
            presence: {
              if: -> { type == "phone" }
            },
            phone: {
              allow_blank: true
            }
  validates :email,
            presence: {
              if: -> { type == "email" }
            },
            phone: {
              allow_blank: true
            }

  encrypts :email, :full_name, :phone, deterministic: true

  normalizes :email, with: EmailAddressNormaliser.new
  normalizes :phone, with: PhoneNumberNormaliser.new
end
