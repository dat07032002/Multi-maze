#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};




// Corresponds to cyberrunner_interfaces__srv__DynamixelReset_Request

// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct DynamixelReset_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub max_temp: u16,

}



impl Default for DynamixelReset_Request {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::srv::rmw::DynamixelReset_Request::default())
  }
}

impl rosidl_runtime_rs::Message for DynamixelReset_Request {
  type RmwMsg = super::srv::rmw::DynamixelReset_Request;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        max_temp: msg.max_temp,
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      max_temp: msg.max_temp,
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      max_temp: msg.max_temp,
    }
  }
}


// Corresponds to cyberrunner_interfaces__srv__DynamixelReset_Response

// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct DynamixelReset_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub success: i8,

}



impl Default for DynamixelReset_Response {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::srv::rmw::DynamixelReset_Response::default())
  }
}

impl rosidl_runtime_rs::Message for DynamixelReset_Response {
  type RmwMsg = super::srv::rmw::DynamixelReset_Response;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        success: msg.success,
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      success: msg.success,
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      success: msg.success,
    }
  }
}






#[link(name = "cyberrunner_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__cyberrunner_interfaces__srv__DynamixelReset() -> *const std::ffi::c_void;
}

// Corresponds to cyberrunner_interfaces__srv__DynamixelReset
#[allow(missing_docs, non_camel_case_types)]
pub struct DynamixelReset;

impl rosidl_runtime_rs::Service for DynamixelReset {
    type Request = DynamixelReset_Request;
    type Response = DynamixelReset_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__cyberrunner_interfaces__srv__DynamixelReset() }
    }
}


