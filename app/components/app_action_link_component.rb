# frozen_string_literal: true

class AppActionLinkComponent < ViewComponent::Base
  def initialize(text:, href:)
    @text = text
    @href = href
  end

  def call
    tag.a(href: @href, class: "nhsuk-action-link") do
      safe_join([icon, tag.span(@text, class: "nhsuk-action-link__text")])
    end
  end

  private

  def icon
    arrow_path = <<~PATH.squish
      M12 2a10 10 0 0 0-10 9h11.7l-4-4a1 1 0 0 1 1.5-1.4l5.6 5.7a1 1 0 0 1 0
      1.4l-5.6 5.7a1 1 0 0 1-1.5 0 1 1 0 0 1 0-1.4l4-4H2A10 10 0 1 0 12 2z
    PATH

    tag.svg(
      class: "nhsuk-icon nhsuk-icon--arrow-right-circle",
      xmlns: "http://www.w3.org/2000/svg",
      viewBox: "0 0 24 24",
      width: "16",
      height: "16",
      focusable: "false",
      aria: {
        hidden: "true"
      }
    ) { tag.path(d: arrow_path) }
  end
end
