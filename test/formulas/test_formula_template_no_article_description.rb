# typed: false
# frozen_string_literal: true

# This file was generated by Homebrew Releaser. DO NOT EDIT.
class TestFormulaTemplateNoArticleDescription < Formula
  desc "Release scripts, binaries, and executables to github"
  homepage "https://github.com/Justintime50/test-formula-template-no-article-description"
  url "https://github.com/Justintime50/test-formula-template-no-article-description/archive/v0.1.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"

  def install
    bin.install "src/secure-browser-kiosk.sh" => "secure-browser-kiosk"
  end
end
