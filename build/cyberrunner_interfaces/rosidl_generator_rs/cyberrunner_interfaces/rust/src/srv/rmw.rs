#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};



#[link(name = "cyberrunner_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__cyberrunner_interfaces__srv__DynamixelReset_Request() -> *const std::ffi::c_void;
}

#[link(name = "cyberrunner_interfaces__rosidl_generator_c")]
extern "C" {
    fn cyberrunner_interfaces__srv__DynamixelReset_Request__init(msg: *mut DynamixelReset_Request) -> bool;
    fn cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<DynamixelReset_Request>, size: usize) -> bool;
    fn cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<DynamixelReset_Request>);
    fn cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<DynamixelReset_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<DynamixelReset_Request>) -> bool;
}

// Corresponds to cyberrunner_interfaces__srv__DynamixelReset_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct DynamixelReset_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub max_temp: u16,

}



impl Default for DynamixelReset_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !cyberrunner_interfaces__srv__DynamixelReset_Request__init(&mut msg as *mut _) {
        panic!("Call to cyberrunner_interfaces__srv__DynamixelReset_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for DynamixelReset_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for DynamixelReset_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for DynamixelReset_Request where Self: Sized {
  const TYPE_NAME: &'static str = "cyberrunner_interfaces/srv/DynamixelReset_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__cyberrunner_interfaces__srv__DynamixelReset_Request() }
  }
}


#[link(name = "cyberrunner_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__cyberrunner_interfaces__srv__DynamixelReset_Response() -> *const std::ffi::c_void;
}

#[link(name = "cyberrunner_interfaces__rosidl_generator_c")]
extern "C" {
    fn cyberrunner_interfaces__srv__DynamixelReset_Response__init(msg: *mut DynamixelReset_Response) -> bool;
    fn cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<DynamixelReset_Response>, size: usize) -> bool;
    fn cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<DynamixelReset_Response>);
    fn cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<DynamixelReset_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<DynamixelReset_Response>) -> bool;
}

// Corresponds to cyberrunner_interfaces__srv__DynamixelReset_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct DynamixelReset_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub success: i8,

}



impl Default for DynamixelReset_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !cyberrunner_interfaces__srv__DynamixelReset_Response__init(&mut msg as *mut _) {
        panic!("Call to cyberrunner_interfaces__srv__DynamixelReset_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for DynamixelReset_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for DynamixelReset_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for DynamixelReset_Response where Self: Sized {
  const TYPE_NAME: &'static str = "cyberrunner_interfaces/srv/DynamixelReset_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__cyberrunner_interfaces__srv__DynamixelReset_Response() }
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


