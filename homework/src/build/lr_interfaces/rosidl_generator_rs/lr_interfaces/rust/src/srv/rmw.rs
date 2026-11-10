#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};



#[link(name = "lr_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__lr_interfaces__srv__Climb_Request() -> *const std::ffi::c_void;
}

#[link(name = "lr_interfaces__rosidl_generator_c")]
extern "C" {
    fn lr_interfaces__srv__Climb_Request__init(msg: *mut Climb_Request) -> bool;
    fn lr_interfaces__srv__Climb_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Climb_Request>, size: usize) -> bool;
    fn lr_interfaces__srv__Climb_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Climb_Request>);
    fn lr_interfaces__srv__Climb_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Climb_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<Climb_Request>) -> bool;
}

// Corresponds to lr_interfaces__srv__Climb_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Climb_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub target_height: i32,

}



impl Default for Climb_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !lr_interfaces__srv__Climb_Request__init(&mut msg as *mut _) {
        panic!("Call to lr_interfaces__srv__Climb_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Climb_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { lr_interfaces__srv__Climb_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { lr_interfaces__srv__Climb_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { lr_interfaces__srv__Climb_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Climb_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Climb_Request where Self: Sized {
  const TYPE_NAME: &'static str = "lr_interfaces/srv/Climb_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__lr_interfaces__srv__Climb_Request() }
  }
}


#[link(name = "lr_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__lr_interfaces__srv__Climb_Response() -> *const std::ffi::c_void;
}

#[link(name = "lr_interfaces__rosidl_generator_c")]
extern "C" {
    fn lr_interfaces__srv__Climb_Response__init(msg: *mut Climb_Response) -> bool;
    fn lr_interfaces__srv__Climb_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Climb_Response>, size: usize) -> bool;
    fn lr_interfaces__srv__Climb_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Climb_Response>);
    fn lr_interfaces__srv__Climb_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Climb_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<Climb_Response>) -> bool;
}

// Corresponds to lr_interfaces__srv__Climb_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Climb_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub current_height: i32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub days: i32,

}



impl Default for Climb_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !lr_interfaces__srv__Climb_Response__init(&mut msg as *mut _) {
        panic!("Call to lr_interfaces__srv__Climb_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Climb_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { lr_interfaces__srv__Climb_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { lr_interfaces__srv__Climb_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { lr_interfaces__srv__Climb_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Climb_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Climb_Response where Self: Sized {
  const TYPE_NAME: &'static str = "lr_interfaces/srv/Climb_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__lr_interfaces__srv__Climb_Response() }
  }
}






#[link(name = "lr_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__lr_interfaces__srv__Climb() -> *const std::ffi::c_void;
}

// Corresponds to lr_interfaces__srv__Climb
#[allow(missing_docs, non_camel_case_types)]
pub struct Climb;

impl rosidl_runtime_rs::Service for Climb {
    type Request = Climb_Request;
    type Response = Climb_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__lr_interfaces__srv__Climb() }
    }
}


