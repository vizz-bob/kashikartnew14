import React, { useState, useEffect, useCallback } from "react";
import { Calendar, Mail, Save, User, Lock, Upload, X } from "lucide-react";
import { getErrorMessage, requestJson, requestWithRetry } from "../utils/api";

const PROFILE_ENDPOINTS = {
  fetch: "/api/user/profile",
  update: "/api/user/profile",
  password: "/api/user/change-password",
};

export default function ProfilePage() {
  // Simulating data that would come from backend API
  const [userData, setUserData] = useState({
    id: null,
    fullName: "",
    email: "",
    phone: "",
    avatar: "",
    role: "",
    joinedDate: "",
    emailVerified: false,
  });

  const [personalInfo, setPersonalInfo] = useState({
    fullName: "",
    email: "",
    phone: "",
  });

  const [securityInfo, setSecurityInfo] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showPhotoMenu, setShowPhotoMenu] = useState(false);
  const [hasCustomPhoto, setHasCustomPhoto] = useState(false);
  const [photoPreview, setPhotoPreview] = useState(null);

  useEffect(() => {
    fetchUserData();
  }, []);

  useEffect(() => {
    const storedName = localStorage.getItem("profileName");
    const storedEmail = localStorage.getItem("profileEmail");
    if (storedName || storedEmail) {
      setUserData((prev) => ({
        ...prev,
        fullName: storedName || prev.fullName,
        email: storedEmail || prev.email,
        avatar: (storedName || prev.fullName)?.charAt(0)?.toUpperCase() || "U",
      }));
      setPersonalInfo((prev) => ({
        ...prev,
        fullName: storedName || prev.fullName,
        email: storedEmail || prev.email,
      }));
    }
  }, []);

  useEffect(() => {
    const storedPhoto = localStorage.getItem("profilePhoto");
    if (storedPhoto) {
      setPhotoPreview(storedPhoto);
      setHasCustomPhoto(true);
    }
  }, []);

  const fetchUserData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await requestWithRetry(() =>
        requestJson(PROFILE_ENDPOINTS.fetch)
      );

      if (!data || typeof data !== "object") {
        throw new Error("Invalid profile response");
      }

      const fullName = data.fullName || data.full_name || "";
      const email = data.email || "";
      const phone = data.phone || "";
      const avatar = fullName?.charAt(0)?.toUpperCase() || "U";
      const role = data.role || data.title || "";
      const joinedDate = data.joinedDate || data.joined_date || "";
      const emailVerified = Boolean(
        data.emailVerified ?? data.email_verified ?? false
      );

      setUserData({
        id: data.id ?? null,
        fullName,
        email,
        phone,
        avatar,
        role,
        joinedDate,
        emailVerified,
      });

      setPersonalInfo({
        fullName,
        email,
        phone,
      });

      // Persist minimal info locally so avatar/name survive reloads.
      localStorage.setItem("profileName", fullName || "");
      localStorage.setItem("profileEmail", email || "");
      window.dispatchEvent(new Event("profileInfoUpdated"));
    } catch (error) {
      console.error("Error fetching user data:", error);
      setError(
        getErrorMessage(error, "Unable to load profile details right now.")
      );
    } finally {
      setLoading(false);
    }
  };

  const handlePersonalInfoChange = useCallback(
    (e) => {
      setPersonalInfo({
        ...personalInfo,
        [e.target.name]: e.target.value,
      });
    },
    [personalInfo]
  );

  const handleSecurityChange = useCallback(
    (e) => {
      setSecurityInfo({
        ...securityInfo,
        [e.target.name]: e.target.value,
      });
    },
    [securityInfo]
  );

  const handleSaveChanges = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await requestWithRetry(() =>
        requestJson(PROFILE_ENDPOINTS.update, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(personalInfo),
        })
      );

      // Update local state after successful save
      setUserData({
        ...userData,
        ...personalInfo,
        avatar: personalInfo.fullName?.charAt(0).toUpperCase() || "U",
      });
      localStorage.setItem("profileName", personalInfo.fullName || "");
      localStorage.setItem("profileEmail", personalInfo.email || "");
      window.dispatchEvent(new Event("profileInfoUpdated"));
      alert("Changes saved successfully!");
    } catch (error) {
      console.error("Error saving changes:", error);
      setError(getErrorMessage(error, "Failed to save changes."));
      alert("Failed to save changes");
    } finally {
      setLoading(false);
    }
  }, [personalInfo, userData]);

  const handleUpdatePassword = useCallback(async () => {
    if (securityInfo.newPassword !== securityInfo.confirmPassword) {
      alert("Passwords do not match!");
      return;
    }

    if (securityInfo.newPassword.length < 8) {
      alert("Password must be at least 8 characters long!");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await requestWithRetry(() =>
        requestJson(PROFILE_ENDPOINTS.password, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            currentPassword: securityInfo.currentPassword,
            newPassword: securityInfo.newPassword,
          }),
        })
      );

      // Clear password fields after successful update
      setSecurityInfo({
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
      });
      alert("Password updated successfully!");
    } catch (error) {
      console.error("Error updating password:", error);
      setError(getErrorMessage(error, "Failed to update password."));
      alert("Failed to update password");
    } finally {
      setLoading(false);
    }
  }, [securityInfo]);

  const handlePhotoUpload = useCallback((e) => {
    const file = e.target.files[0];
    if (file) {
      // Create preview URL
      const reader = new FileReader();
      reader.onloadend = () => {
        setPhotoPreview(reader.result);
        setHasCustomPhoto(true);
        setShowPhotoMenu(false);
        localStorage.setItem("profilePhoto", reader.result);
        window.dispatchEvent(new Event("profilePhotoUpdated"));

        // Here you would upload to your backend
        console.log("Uploading photo:", file);
        alert("Photo uploaded successfully!");
      };
      reader.readAsDataURL(file);
    }
  }, []);

  const handleRemovePhoto = useCallback(() => {
    // Handle photo removal logic here
    console.log("Removing photo");
    setPhotoPreview(null);
    setHasCustomPhoto(false);
    setShowPhotoMenu(false);
    localStorage.removeItem("profilePhoto");
    window.dispatchEvent(new Event("profilePhotoUpdated"));
    alert("Photo removed successfully!");
  }, []);

  if (loading && !userData.id) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#2b7fff] mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-gray-50">
      {/* Page Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-6 mb-8 sm:px-8">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-3xl font-semibold text-gray-900">Profile</h1>
          <p className="text-gray-500 text-sm mt-1">
            Manage your account settings
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-8">
        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}
        <div className="grid md:grid-cols-3 gap-6">
          {/* Left Sidebar Card */}
          <div className="md:col-span-1">
            <div className="bg-white rounded-xl shadow-sm p-6 sticky top-8">
              <div className="text-center">
                {/* Profile Photo with Menu */}
                <div className="relative inline-block mb-4">
                  {photoPreview ? (
                    <img
                      src={photoPreview}
                      alt="Profile"
                      className="w-28 h-28 rounded-full object-cover shadow-lg"
                    />
                  ) : (
                    <div className="w-28 h-28 rounded-full bg-[#2b7fff] flex items-center justify-center text-white text-3xl font-bold shadow-lg">
                      {userData.avatar || userData.fullName?.charAt(0) || "U"}
                    </div>
                  )}

                  {/* Photo Upload Button */}
                  <button
                    onClick={() => setShowPhotoMenu(!showPhotoMenu)}
                    className="absolute bottom-0 right-0 bg-[#2b7fff] p-2 rounded-full text-white hover:bg-[#1a6eef] shadow-lg transition-all"
                  >
                    <Upload className="w-4 h-4" />
                  </button>

                  {/* Photo Menu Dropdown */}
                  {showPhotoMenu && (
                    <div className="absolute top-full right-0 mt-2 bg-white rounded-lg shadow-xl border border-gray-200 py-2 w-48 z-10">
                      <label className="flex items-center gap-3 px-4 py-2 hover:bg-gray-50 cursor-pointer transition-colors">
                        <Upload className="w-4 h-4 text-gray-600" />
                        <span className="text-sm text-gray-700">
                          Upload Photo
                        </span>
                        <input
                          type="file"
                          accept="image/*"
                          className="hidden"
                          onChange={handlePhotoUpload}
                        />
                      </label>
                      {hasCustomPhoto && (
                        <button
                          onClick={handleRemovePhoto}
                          className="flex items-center gap-3 px-4 py-2 hover:bg-gray-50 w-full text-left transition-colors"
                        >
                          <X className="w-4 h-4 text-red-600" />
                          <span className="text-sm text-red-600">
                            Remove Photo
                          </span>
                        </button>
                      )}
                    </div>
                  )}
                </div>

                <h2 className="text-xl font-bold text-gray-900 mb-1">
                  {userData.fullName}
                </h2>
                <p className="text-sm text-gray-500 mb-4">{userData.email}</p>
                <span className="inline-block px-4 py-1.5 bg-[#2b7fff] text-white rounded-full text-sm font-medium">
                  {userData.role}
                </span>
              </div>

              <div className="mt-6 pt-6 border-t border-gray-100 space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Status</span>
                  <span className="flex items-center gap-1 text-green-600 font-medium">
                    <svg
                      className="w-4 h-4"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                    Verified
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Member Since</span>
                  <span className="text-gray-900 font-medium">
                    {userData.joinedDate}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="md:col-span-2 space-y-6">
            {/* Personal Information Card */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-center gap-2 mb-6">
                <div className="p-2 bg-[#2b7fff]/10 rounded-lg">
                  <User className="w-5 h-5 text-[#2b7fff]" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Personal Information
                </h3>
              </div>
              <div className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Full Name
                    </label>
                    <input
                      type="text"
                      name="fullName"
                      value={personalInfo.fullName}
                      onChange={handlePersonalInfoChange}
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#2b7fff] focus:border-transparent outline-none transition"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Email Address
                    </label>
                    <input
                      type="email"
                      name="email"
                      value={personalInfo.email}
                      onChange={handlePersonalInfoChange}
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Phone Number
                  </label>
                  <input
                    type="tel"
                    name="phone"
                    value={personalInfo.phone}
                    onChange={handlePersonalInfoChange}
                    placeholder="Enter your phone number"
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                  />
                </div>
                <div className="pt-2">
                  <button
                    onClick={handleSaveChanges}
                    disabled={loading}
                    className="w-full px-6 py-2.5 bg-[#2b7fff] text-white rounded-lg hover:bg-[#1a6eef] font-medium flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition"
                  >
                    <Save className="w-4 h-4" />
                    Update Information
                  </button>
                </div>
              </div>
            </div>

            {/* Privacy Settings Card */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-center gap-2 mb-6">
                <div className="p-2 bg-[#2b7fff]/10 rounded-lg">
                  <Lock className="w-5 h-5 text-[#2b7fff]" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Privacy Settings
                </h3>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Current Password
                  </label>
                  <input
                    type="password"
                    name="currentPassword"
                    value={securityInfo.currentPassword}
                    onChange={handleSecurityChange}
                    placeholder="Enter current password"
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                  />
                </div>
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      New Password
                    </label>
                    <input
                      type="password"
                      name="newPassword"
                      value={securityInfo.newPassword}
                      onChange={handleSecurityChange}
                      placeholder="Enter new password"
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Confirm Password
                    </label>
                    <input
                      type="password"
                      name="confirmPassword"
                      value={securityInfo.confirmPassword}
                      onChange={handleSecurityChange}
                      placeholder="Confirm new password"
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                    />
                  </div>
                </div>
                <div className="pt-2">
                  <button
                    onClick={handleUpdatePassword}
                    disabled={loading}
                    className="w-full px-6 py-2.5 bg-[#2b7fff] text-white rounded-lg hover:bg-[#1a6eef] font-medium disabled:opacity-50 disabled:cursor-not-allowed transition"
                  >
                    Update Password
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
